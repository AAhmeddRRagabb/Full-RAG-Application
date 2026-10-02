# ------------------------------------------------------
# Implementing the routes related to the NLP workflows
# -------------------------------------------------------


# utils
import asyncio
import json
import logging
import time
logger = logging.getLogger("uvicorn")

import helpers.config as CFG
from helpers.functional import raise_internal_server_error
from typing import Annotated, Any, Awaitable, Callable


# controllers
from controllers import VectorDBController
from controllers import ChatController

# fastapi utils
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status
from fastapi.responses import StreamingResponse

# models & schemas
from models.db_objects_models import AssetModel, ChatModel, ChunkModel, RunModel
from models.system_schemas import AuthContext
from models.db_schemas import Chat, Message, Run, RunStep, User
from models.request_schemas.chat import ChatRequest


# clients
from clients.vector_dbs.vector_db_clients import PGVectorVDBClient
from clients.llms.llm_clients import HuggingfaceLLMClient, GoogleLLMClient, GroqLLMClient
from clients.llms.prompt_templates import PromptTemplateParser
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from tavily import TavilyClient

# dependecies
from app_core.dependecies.auth import require_authentication, require_csrf
from app_core.dependecies.clients import (
    get_redis,
    get_embedding_client, 
    get_vector_db_client, 
    get_prompt_template_parser, 
    get_llm_clients,
    get_db_client,
    get_tavily_client
)
from app_core.dependecies.rate_limit import check_rate_limit



chat_router = APIRouter(
    prefix = CFG.CHAT_ROUTER_PATH,
    tags = ["nlp"]
)





from helpers.chat import (
    build_public_chat,
    build_public_message,
    get_file_name,
    calc_run_time_s,
    get_messages_content
)


# ------------------------- Accessing Chats / messages ---------------------------------- #
@chat_router.get("/chats")
async def get_user_chats(
    auth     : Annotated[AuthContext, Depends(require_authentication)],
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
):
    chat_model = ChatModel(db_client = db_client)
    chats = await chat_model.get_user_chats(user_id = auth.user.user_id)

    if chats is None:
        raise raise_internal_server_error()

    return {
        "chats": [build_public_chat(chat) for chat in chats]
    }


@chat_router.get("/chats/{chat_id}")
async def get_user_chat(
    auth     : Annotated[AuthContext, Depends(require_authentication)],
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
    chat_id  : int,
):
    # - access chat
    chat_model = ChatModel(db_client = db_client)
    chat = await chat_model.get_user_chat(
        user_id = auth.user.user_id,
        chat_id = chat_id,
    )

    if chat is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = "Chat not found",
        )

    # - access messages
    messages = await chat_model.get_chat_messages(
        user_id = auth.user.user_id,
        chat_id = chat_id,
    )

    if messages is None:
        raise raise_internal_server_error()

    return {
        "chat"    : build_public_chat(chat),
        "messages": [build_public_message(message) for message in messages]
    }


@chat_router.get("/chats/{chat_id}/messages")
async def get_chat_messages(
    auth     : Annotated[AuthContext, Depends(require_authentication)],
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
    chat_id  : int,
):
    chat_model = ChatModel(db_client = db_client)
    chat = await chat_model.get_user_chat(
        user_id = auth.user.user_id,
        chat_id = chat_id,
    )

    if chat is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Chat not found",
        )

    messages = await chat_model.get_chat_messages(
        user_id = auth.user.user_id,
        chat_id = chat_id,
    )

    if messages is None:
        raise raise_internal_server_error()

    return {
        "messages": [
            build_public_message(message) for message in messages
        ],
    }

# ------------------------- Add / Edit / Delete Chats ---------------------------------- #
@chat_router.post("/chats", status_code = status.HTTP_201_CREATED)
async def create_user_chat(
    auth     : Annotated[AuthContext, Depends(require_csrf)],
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
    chat_name: str,
):
    # - setup
    chat_model = ChatModel(db_client = db_client)
    user_chats = await chat_model.get_user_chats(user_id = auth.user.user_id)

    if user_chats is None:
        raise raise_internal_server_error()

    # - create chat
    chat = Chat(
        user_id   = auth.user.user_id,
        chat_name = chat_name
    )

    if not await chat_model.insert_chat(chat):
        raise raise_internal_server_error()

    return {
        "chat": build_public_chat(chat),
    }


@chat_router.patch("/chats/{chat_id}")
async def rename_user_chat(
    auth     : Annotated[AuthContext, Depends(require_csrf)],
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
    chat_id  : int,
    chat_name: str,
):
    # - setup
    if not chat_name:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Chat name is required",
        )

    chat_model = ChatModel(db_client = db_client)

    # - update name
    chat = await chat_model.update_chat_name(
        user_id   = auth.user.user_id,
        chat_id   = chat_id,
        chat_name = chat_name.strip(),
    )

    if chat is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = "Chat not found",
        )

    return {
        "chat": build_public_chat(chat),
    }



@chat_router.delete("/chats/{chat_id}")
async def delete_user_chat(
    auth     : Annotated[AuthContext, Depends(require_csrf)],
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
    chat_id  : int,
):
    chat_model = ChatModel(db_client = db_client)

    if not await chat_model.delete_user_chat(
        user_id = auth.user.user_id,
        chat_id = chat_id,
    ):
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Chat not found",
        )

    return {
        "message": "Chat deleted successfully",
    }


# ---------------------------------- Chatting -------------------------------- #

def stream_event(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default = str) + "\n"


def stage_label(stage: str) -> str:
    parsing_stages = {
        "preparing",
        "rate_limit",
        "loading_chat",
        "saving_message",
        "understand_user_query",
        "get_chat_context",
    }

    finalizing_stages = {
        "generate_final_report",
        "finish",
    }

    if stage in parsing_stages:
        return "parsing query"

    if stage in finalizing_stages:
        return "finalizing response"

    return "thinking"


def log_detached_task_failure(task: asyncio.Task) -> None:
    try:
        exception = task.exception()
    except asyncio.CancelledError:
        return None

    if exception:
        logger.error(
            "Detached chat run failed",
            exc_info = (type(exception), exception, exception.__traceback__),
        )


# logic should be:-
# ---> understand query with chat context
# ---> Search for answers [basic - moderate - advanced] searches
# ---> generate answer

async def run_chat_request(
    request  : Request,
    auth     : AuthContext,
    db_client: AsyncSession,
    
    redis                 : Redis,
    vector_db_client      : PGVectorVDBClient,
    embedding_client      : HuggingfaceLLMClient | GoogleLLMClient,
    llm_clients           : dict[str, HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient | list[HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient]],
    prompt_template_parser: PromptTemplateParser,
    tavily_client         : TavilyClient,

    chat_request  : ChatRequest,
    stage_callback: Callable[[str], Awaitable[None]] | None = None,
) -> dict:

    started_at = time.perf_counter()
    async def emit(stage: str) -> None:
        if stage_callback is not None:
            await stage_callback(stage)

    await emit("rate_limit")
    client_host = request.client.host if request.client else "unknown"
    await check_rate_limit(redis, f"chat:ip:{client_host}", limit = 100, window_seconds = 3600)
    await check_rate_limit(redis, f"chat:user:{auth.user.user_uuid}", limit = 30, window_seconds = 3600)

    # - setup
    vector_db_controller = VectorDBController(vector_db_client, embedding_client)
    chat_controller = ChatController(llm_clients, prompt_template_parser, tavily_client)

    chunk_model = ChunkModel(db_client = db_client)
    chat_model  = ChatModel(db_client = db_client)
    asset_model = AssetModel(db_client = db_client)
    run_model   = RunModel(db_client = db_client)

    user: User = auth.user
    user_key   = user.user_uuid.hex


    query   = chat_request.query
    chat_id = chat_request.chat_id
    tone    = chat_request.tone
    depth   = chat_request.depth
    files   = chat_request.files

 
    await emit("loading_chat")
    active_chat = await chat_model.get_user_chat(user_id = user.user_id, chat_id = chat_id)
    if active_chat is None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Chat not found")

    # - start the Run
    # run = Run(
    #     user_id = user.user_id,
    #     chat_id = active_chat.chat_id,
    #     user_query = query,
    #     run_metadata = {
    #         "files": [get_file_name(file) for file in files]
    #     },
    # )

    # if not await run_model.insert_run(run):
    #     raise raise_internal_server_error()


    previous_messages = await chat_model.get_chat_messages(
        user_id = user.user_id,
        chat_id = active_chat.chat_id,
    )

    # if previous_messages is None:
    #     await run_model.fail_run(
    #         run_id = run.run_id, 
    #         error = "Could not load chat messages", 
    #         time_taken = calc_run_time_s(started_at)
    #     )
    #     raise raise_internal_server_error()


    await emit("saving_message")
    # if not await chat_model.insert_message(
    #     Message(
    #         chat_id = active_chat.chat_id,
    #         role    = "user",
    #         content = query,
    #     )
    # ):
    #     await run_model.fail_run(
    #         run_id = run.run_id, 
    #         error = "Could not save user message", 
    #         time_taken = calc_run_time_s(started_at)
    #     )

    #     raise_internal_server_error()

    
    # --------------------- Begin Agentic Work ----------------------------- #
    from helpers.chat import get_chat_cfg

    agent_result = await chat_controller.answer_user_query(
        user_query = query,
        files = files or [],
        chat_cfg = get_chat_cfg(
            chat_tone = tone,
            chat_depth = depth,
        ),
        chat_messages = get_messages_content(previous_messages),
        stage_callback = emit,
    )

    return {}

    if agent_result is None:
        await fail_run("Agent failed to produce a result")
        raise_internal_server_error()

    report = agent_result.get("report")
    resources = agent_result.get("llm_resources") or []

    if not await chat_model.insert_message(
        Message(
            chat_id       = active_chat.chat_id,
            role          = "assistant",
            content       = report or "",
            llm_resources = resources
        )
    ):
        await fail_run("Could not save assistant message", response = report)
        raise_internal_server_error()

    steps = [
        RunStep(
            run_id = run.run_id,
            step_order = idx,
            step_name = step.get("name", "unknown"),
            step_input = step.get("input"),
            step_output = step.get("output"),
            duration_ms = step.get("duration_ms"),
        )
        for idx, step in enumerate(agent_result.get("steps") or [], start = 1)
    ]

    if not await run_model.insert_steps(steps):
        logger.error(f"Error saving run steps. Run ID: {run.run_id}")

    await run_model.finish_run(
        run_id = run.run_id,
        status = "success",
        response = report,
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2),
    )
    
    return {
        "report"              : report,
        "llm_resources"       : resources,
        "run_id"              : run.run_id,
    }


@chat_router.post("/chat/stream")
async def stream_chat_will_llm(
    request               : Request,
    auth                  : Annotated[AuthContext, Depends(require_csrf)],
    db_client             : Annotated[AsyncSession, Depends(get_db_client)],
    redis                 : Annotated[Redis, Depends(get_redis)],
    vector_db_client      : Annotated[PGVectorVDBClient, Depends(get_vector_db_client)],
    embedding_client      : Annotated[HuggingfaceLLMClient | GoogleLLMClient, Depends(get_embedding_client)],
    llm_clients           : Annotated[dict[str, HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient | list[HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient]], Depends(get_llm_clients)],
    prompt_template_parser: Annotated[PromptTemplateParser, Depends(get_prompt_template_parser)],
    tavily_client         : Annotated[TavilyClient, Depends(get_tavily_client)],
    chat_request          : ChatRequest,
):
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    last_stage_message: str | None = None

    async def emit(stage: str) -> None:
        nonlocal last_stage_message

        message = stage_label(stage)
        if message == last_stage_message:
            return

        last_stage_message = message
        await queue.put({
            "type": "stage",
            "stage": stage,
            "message": message,
        })

    async def produce() -> None:
        try:
            result = await run_chat_request(
                request = request,
                auth = auth,
                db_client = db_client,
                redis = redis,
                vector_db_client = vector_db_client,
                embedding_client = embedding_client,
                llm_clients = llm_clients,
                prompt_template_parser = prompt_template_parser,
                tavily_client = tavily_client,
                chat_request = chat_request,
                stage_callback = emit,
            )
            await queue.put({"type": "result", "data": result})

        except HTTPException as e:
            await queue.put({
                "type": "error",
                "status_code": e.status_code,
                "detail": e.detail,
            })

        except Exception:
            logger.exception("Streaming chat failed")
            await queue.put({
                "type": "error",
                "status_code": 500,
                "detail": "Internal server error",
            })

        finally:
            await queue.put(None)

    async def events():
        nonlocal last_stage_message

        task = asyncio.create_task(produce())
        task.add_done_callback(log_detached_task_failure)

        try:
            last_stage_message = stage_label("preparing")
            yield stream_event({
                "type": "stage",
                "stage": "preparing",
                "message": last_stage_message,
            })

            while True:
                item = await queue.get()
                if item is None:
                    break

                if item.get("type") == "result":
                    data = item["data"]
                    report = data.get("report") or ""

                    for token in report.split(" "):
                        if token:
                            yield stream_event({
                                "type": "token",
                                "value": f"{token} ",
                            })

                    yield stream_event({
                        "type": "done",
                        **data,
                    })
                    continue

                yield stream_event(item)

        finally:
            pass

    return StreamingResponse(
        events(),
        media_type = "application/x-ndjson",
    )

