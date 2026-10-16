import asyncio
import json
import logging
import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import status
from fastapi.responses import StreamingResponse
from tavily import TavilyClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependecies.auth import require_authentication, require_csrf
from core.dependecies.clients import (
    get_redis,
    get_embedding_client, 
    get_vector_db_client, 
    get_prompt_template_parser, 
    get_llm_clients,
    get_db_client,
    get_tavily_client
)
from core.helpers import check_rate_limit
from clients.llms.llm_clients import GoogleLLMClient, GroqLLMClient, HuggingfaceLLMClient
from clients.llms.prompt_templates import PromptTemplateParser
from clients.vector_dbs.vector_db_clients import PGVectorVDBClient
from controllers import ChatController, VectorDBController
import core.system_settings as CFG
from core.chat import (
    calc_run_time_s,
    emit,
    get_chat_cfg,
    get_file_name,
    get_messages_content,
    log_run_step
)
from core.helpers import build_public_chat, build_public_message, raise_internal_server_error
from models.db_models import AssetModel, ChatModel, ChunkModel, RunModel
from models.db_schemas import Chat, Message, Run, RunStep, User
from models.enums import ResponsesEnum
from models.api_schemas import ChatRequest
from models.db_schemas.redis_data import AuthContext


logger = logging.getLogger("uvicorn")

chat_router = APIRouter(
    prefix = CFG.CHAT_ROUTER_PATH,
    tags = ["nlp"]
)


PARSING_QUERY_MESSAGE = "Parsing Query..."


# ------------------------- Accessing Chats / messages ---------------------------------- #
@chat_router.get("/chats")
async def get_user_chats(
    auth     : Annotated[AuthContext, Depends(require_authentication)],
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
):
    chat_model = ChatModel(db_client = db_client)
    chats = await chat_model.get_user_chats(user_id = auth.user.user_id)

    if chats is None:
        raise_internal_server_error()

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
            detail      = ResponsesEnum.CHAT_NOT_FOUND.value,
        )

    # - access messages
    messages = await chat_model.get_chat_messages(
        user_id = auth.user.user_id,
        chat_id = chat_id,
    )

    if messages is None:
        raise_internal_server_error()

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
            detail = ResponsesEnum.CHAT_NOT_FOUND.value,
        )

    messages = await chat_model.get_chat_messages(
        user_id = auth.user.user_id,
        chat_id = chat_id,
    )

    if messages is None:
        raise_internal_server_error()

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
        raise_internal_server_error()

    # - create chat
    chat = Chat(
        user_id   = auth.user.user_id,
        chat_name = chat_name
    )

    if not await chat_model.insert_chat(chat):
        raise_internal_server_error()

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
            detail = ResponsesEnum.CHAT_NAME_REQUIRED.value,
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
            detail      = ResponsesEnum.CHAT_NOT_FOUND.value,
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
            detail = ResponsesEnum.CHAT_NOT_FOUND.value,
        )

    return {
        "message": ResponsesEnum.CHAT_DELETED_SUCCESSFULLY.value,
    }


# ---------------------------------- Chatting -------------------------------- #

def stream_event(payload: dict[str, Any]) -> str:
    return json.dumps(payload, default = str) + "\n"


async def run_chat_request(
    request     : Request,
    chat_request: ChatRequest,
    queue       : asyncio.Queue,

    auth                  : AuthContext,
    db_client             : AsyncSession,
    redis                 : Redis,
    vector_db_client      : PGVectorVDBClient,
    embedding_client      : HuggingfaceLLMClient | GoogleLLMClient,
    llm_clients           : dict[str, HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient | list[HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient]],
    prompt_template_parser: PromptTemplateParser,
    tavily_client         : TavilyClient,
) -> dict:

    # ------------------------------------ Setup ------------------------------------ #
    # - define variables
    started_at = time.perf_counter()

    user: User = auth.user
    user_uuid  = user.user_uuid

    query   = chat_request.query
    chat_id = chat_request.chat_id
    tone    = chat_request.tone
    depth   = chat_request.depth
    files   = chat_request.files or []

    client_host = request.client.host if request.client else "unknown"


    # - define models & controllers
    chunk_model = ChunkModel(db_client = db_client)
    chat_model  = ChatModel(db_client = db_client)
    asset_model = AssetModel(db_client = db_client)
    run_model   = RunModel(db_client = db_client)

    vector_db_controller = VectorDBController(vector_db_client, embedding_client)
    chat_controller = ChatController(
        llm_clients = llm_clients, 
        prompt_template_parser = prompt_template_parser, 
        tavily_client = tavily_client,
        user = user,
        asset_model = asset_model,
        chunk_model = chunk_model,
        vector_db_controller = vector_db_controller
    )

    # ------------------------------------ Start Working ------------------------------------ #

    # - limit rate
    await emit(queue = queue, message = PARSING_QUERY_MESSAGE)
    await check_rate_limit(redis, f"chat:ip:{client_host}", limit = 100, window_seconds = 3600)
    await check_rate_limit(redis, f"chat:user:{user_uuid}", limit = 30, window_seconds = 3600)


    # - load chat
    active_chat = await chat_model.get_user_chat(user_id = user.user_id, chat_id = chat_id)
    if active_chat is None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = ResponsesEnum.CHAT_NOT_FOUND.value)

    previous_messages = await chat_model.get_chat_messages(
        user_id = user.user_id,
        chat_id = active_chat.chat_id,
    )


    # - start the Run
    run = Run(
        user_id = user.user_id,
        chat_id = active_chat.chat_id,
        user_query = query,
        run_metadata = {
            "files": [get_file_name(file) for file in files],
            "tone": tone,
            "depth": depth,
        },
    )

    if not await run_model.insert_run(run):
        raise_internal_server_error()


    if previous_messages is None:
        await run_model.fail_run(
            run_id = run.run_id, 
            error = "Could not load chat messages", 
            time_taken = calc_run_time_s(started_at)
        )
        raise_internal_server_error()


    if not await chat_model.insert_message(
        Message(
            chat_id = active_chat.chat_id,
            role    = "user",
            content = query,
        )
    ):
        await run_model.fail_run(
            run_id = run.run_id, 
            error = "Could not save user message", 
            time_taken = calc_run_time_s(started_at)
        )

        raise_internal_server_error()

    # --------------------- Agentic Work ----------------------------- #
    step_order = 0

    async def record_run_step(step: dict[str, Any]) -> None:
        nonlocal step_order
        await log_run_step(run_model, run, step, step_order)
        step_order += 1

    try:
        agent_result = await chat_controller.answer_user_query(
            user_query = query,
            files = files,
            chat_cfg = get_chat_cfg(
                chat_tone = tone,
                chat_depth = depth,
            ),
            chat_messages = previous_messages,
            queue = queue,
            run_step_logger = record_run_step,
        )


    except Exception as e:
        await run_model.fail_run(
            run_id = run.run_id,
            error = str(e),
            time_taken = calc_run_time_s(started_at),
        )
        raise_internal_server_error()

    if agent_result is None:
        await run_model.fail_run(
            run_id = run.run_id,
            error = "Agent failed to produce a result",
            time_taken = calc_run_time_s(started_at),
        )
        raise_internal_server_error()

    report = agent_result.get("answer")
    resources = agent_result.get("resources") or []

    if not await chat_model.insert_message(
        Message(
            chat_id       = active_chat.chat_id,
            role          = "assistant",
            content       = report or "",
            llm_resources = resources
        )
    ):
        await run_model.fail_run(
            run_id = run.run_id,
            error = "Could not save assistant message",
            time_taken = calc_run_time_s(started_at),
            response = report,
        )
        raise_internal_server_error()

    await run_model.finish_run(
        run_id = run.run_id,
        status = "success",
        response = report,
        duration_s = calc_run_time_s(started_at),
    )
    
    return {
        "report"              : report,
        "llm_resources"       : resources,
        "run_id"              : run.run_id,
    }


@chat_router.post("/chat/stream")
async def stream_chat_will_llm(
    request     : Request,
    chat_request: ChatRequest,

    auth                  : Annotated[AuthContext, Depends(require_csrf)],
    db_client             : Annotated[AsyncSession, Depends(get_db_client)],
    redis                 : Annotated[Redis, Depends(get_redis)],
    vector_db_client      : Annotated[PGVectorVDBClient, Depends(get_vector_db_client)],
    embedding_client      : Annotated[HuggingfaceLLMClient | GoogleLLMClient, Depends(get_embedding_client)],
    llm_clients           : Annotated[dict[str, HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient | list[HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient]], Depends(get_llm_clients)],
    prompt_template_parser: Annotated[PromptTemplateParser, Depends(get_prompt_template_parser)],
    tavily_client         : Annotated[TavilyClient, Depends(get_tavily_client)],
):
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

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
                queue = queue
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
                "detail": ResponsesEnum.INTERNAL_SERVER_ERROR.value,
            })

        finally:
            await queue.put(None)

    async def events():
        asyncio.create_task(produce())

        while True:
            item = await queue.get()
            if item is None:
                break

            if item.get("type") != "result":
                yield stream_event(item)
                continue

            data = item["data"]
            for token in (data.get("report") or "").split(" "):
                if token:
                    yield stream_event({"type": "token", "value": f"{token} "})

            yield stream_event({"type": "done", **data})

    return StreamingResponse(
        events(),
        media_type = "application/x-ndjson",
    )
