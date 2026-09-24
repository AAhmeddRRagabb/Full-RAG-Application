# ------------------------------------------------------
# Implementing the routes related to the NLP workflows
# -------------------------------------------------------


# utils
import logging
logger = logging.getLogger("uvicorn")

import helpers.config as CFG
from helpers.functional import raise_internal_server_error
from typing import Annotated
from helpers.config import get_settings


# controllers
from controllers import VectorDBController
from controllers import ChatController

# fastapi utils
from fastapi import APIRouter, Depends, HTTPException
from fastapi import status

# models & schemas
from models.db_objects_models import ChatModel, ChunkModel
from models.system_schemas import AuthContext
from models.db_schemas import Chat, Message, User
from models.request_schemas.chat import (
    ChatSettings,
    ChatPublic,
    ChatRequest,
    CreateChatRequest,
    MessagePublic,
    RenameChatRequest,
    UpdateChatSettingsRequest,
)


# clients
from clients.vector_dbs.vector_db_clients import PGVectorVDBClient
from clients.llms.llm_clients import HuggingfaceLLMClient, GoogleLLMClient, GroqLLMClient
from clients.llms.prompt_templates import PromptTemplateParser
from sqlalchemy.ext.asyncio import AsyncSession
from tavily import TavilyClient

# dependecies
from app_core.dependecies.auth import require_authentication
from app_core.dependecies.clients import (
    get_embedding_client, 
    get_vector_db_client, 
    get_prompt_template_parser, 
    get_llm_clients,
    get_db_client,
    get_tavily_client
)



chat_router = APIRouter(
    prefix = CFG.CHAT_ROUTER_PATH,
    tags = ["nlp"]
)


DEFAULT_CHAT_SETTINGS = ChatSettings()


TONE_MODEL_CONFIGURATIONS = {
    "technical": {
        "temperature": 0.0,
        "max_tokens": 512,
        "top_p": 0.85,
    },
    "creative": {
        "temperature": 0.9,
        "max_tokens": 1024,
        "top_p": 0.95,
    },
}


def clean_chat_name(chat_name: str | None, fallback: str = 'chat_abc') -> str:
    chat_name = (chat_name or "").strip()
    return chat_name or fallback


def normalize_chat_settings(settings: dict | ChatSettings | None = None) -> dict:
    if isinstance(settings, ChatSettings):
        settings = settings.model_dump()

    settings = settings or {}
    tone = settings.get("tone") or DEFAULT_CHAT_SETTINGS.tone

    if tone not in ["technical", "creative", "custom"]:
        tone = DEFAULT_CHAT_SETTINGS.tone

    return ChatSettings(
        search_online = bool(settings.get("search_online", DEFAULT_CHAT_SETTINGS.search_online)),
        files = settings.get("files", DEFAULT_CHAT_SETTINGS.files),
        tone = tone,
        model_configurations = settings.get("model_configurations") if tone == "custom" else None,
    ).model_dump()


def resolve_model_configurations(settings: dict) -> dict | None:
    if settings["tone"] == "custom":
        return settings.get("model_configurations")

    return TONE_MODEL_CONFIGURATIONS.get(settings["tone"])


def merge_chat_settings(chat: Chat, new_settings: ChatSettings | None = None) -> dict:
    base_settings = normalize_chat_settings(chat.chat_settings)

    if new_settings is None:
        return base_settings

    new_settings = new_settings.model_dump()
    base_settings.update(normalize_chat_settings(new_settings))
    return normalize_chat_settings(base_settings)



def build_public_chat(chat: Chat) -> ChatPublic:
    return ChatPublic(
        chat_id   = chat.chat_id,
        chat_name = chat.chat_name,
        settings  = ChatSettings.model_validate(normalize_chat_settings(chat.chat_settings)),
    )


def build_public_message(message: Message) -> MessagePublic:
    return MessagePublic(
        message_id = message.message_id,
        chat_id = message.chat_id,
        role = message.role,
        content = message.content,
        llm_resources = message.llm_resources,
        created_at = message.created_at,
    )




# ------------------------- Accessing User Chats ---------------------------------- #
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
            detail      = "Chat not found",
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


# ------------------------- Add / Edit / Delete Chats ---------------------------------- #
@chat_router.post("/chats", status_code = status.HTTP_201_CREATED)
async def create_user_chat(
    auth               : Annotated[AuthContext, Depends(require_authentication)],
    db_client          : Annotated[AsyncSession, Depends(get_db_client)],
    create_chat_request: CreateChatRequest,
):
    # - setup
    chat_model = ChatModel(db_client = db_client)
    user_chats = await chat_model.get_user_chats(user_id = auth.user.user_id)

    if user_chats is None:
        raise_internal_server_error()

    # - create chat
    chat = Chat(
        user_id   = auth.user.user_id,
        chat_name = clean_chat_name(
            chat_name = create_chat_request.chat_name,
            fallback  = f"chat #{len(user_chats) + 1}",
        ),
        chat_settings = normalize_chat_settings(),
    )

    if not await chat_model.insert_chat(chat):
        raise_internal_server_error()

    return {
        "chat": build_public_chat(chat),
    }


@chat_router.patch("/chats/{chat_id}")
async def rename_user_chat(
    auth               : Annotated[AuthContext, Depends(require_authentication)],
    db_client          : Annotated[AsyncSession, Depends(get_db_client)],
    chat_id            : int,
    rename_chat_request: RenameChatRequest,
):
    # - setup
    chat_name = rename_chat_request.chat_name.strip()
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
        chat_name = chat_name,
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
    auth     : Annotated[AuthContext, Depends(require_authentication)],
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


# ---------------------------------- Manage Chat Settings -------------------------------- #
@chat_router.patch("/chats/{chat_id}/settings")
async def update_user_chat_settings(
    auth                        : Annotated[AuthContext, Depends(require_authentication)],
    db_client                   : Annotated[AsyncSession, Depends(get_db_client)],
    chat_id                     : int,
    update_chat_settings_request: UpdateChatSettingsRequest,
):
    # - setup
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

    # - update settings
    chat = await chat_model.update_chat_settings(
        user_id       = auth.user.user_id,
        chat_id       = chat_id,
        chat_settings = merge_chat_settings(
            chat = chat,
            new_settings = update_chat_settings_request.settings,
        ),
    )

    if chat is None:
        raise_internal_server_error()

    return {
        "chat": build_public_chat(chat),
    }


@chat_router.get("/chats/{chat_id}/messages")
async def get_user_chat_messages(
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
        raise_internal_server_error()

    return {
        "messages": [
            build_public_message(message) for message in messages
        ],
    }


# ---------------------------------- Send a Query to LLMs -------------------------------- #
@chat_router.post("/chat")
async def chat_will_llm(
    auth                  : Annotated[AuthContext, Depends(require_authentication)],
    db_client             : Annotated[AsyncSession, Depends(get_db_client)],
    vector_db_client      : Annotated[PGVectorVDBClient, Depends(get_vector_db_client)],
    embedding_client      : Annotated[HuggingfaceLLMClient | GoogleLLMClient, Depends(get_embedding_client)],
    llm_clients           : Annotated[dict[str, HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient], Depends(get_llm_clients)],
    prompt_template_parser: Annotated[PromptTemplateParser, Depends(get_prompt_template_parser)],
    tavily_client         : Annotated[TavilyClient, Depends(get_tavily_client)],
    chat_request          : ChatRequest
):
    # - setup
    vector_db_controller = VectorDBController(vector_db_client = vector_db_client, embedding_client = embedding_client)
    chat_controller = ChatController(prompt_template_parser = prompt_template_parser, llm_clients = llm_clients, tavily_client = tavily_client)

    chunk_model = ChunkModel(db_client = db_client)
    chat_model = ChatModel(db_client = db_client)
    user: User = auth.user
    query = chat_request.query

    # - acquire chat settings
    active_chat = await chat_model.get_user_chat(user_id = user.user_id, chat_id = chat_request.chat_id)
    if active_chat is None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Chat not found")

    chat_settings = merge_chat_settings(chat = active_chat, new_settings = chat_request.settings)
    files = chat_settings["files"]
    model_configurations = resolve_model_configurations(chat_settings)


    if chat_request.settings is not None:
        active_chat = await chat_model.update_chat_settings(
            user_id       = user.user_id,
            chat_id       = chat_request.chat_id,
            chat_settings = chat_settings,
        )

        if active_chat is None:
            raise_internal_server_error()


    if not await chat_model.insert_message(
        Message(
            chat_id = active_chat.chat_id,
            role    = "user",
            content = query,
        )
    ):
        raise_internal_server_error()

    
    # --------------------- Begin Agentic Work ----------------------------- #
    async def search_file_chunks(query: str, file: str, retrieve_limit: int):
        try:
            file_id, _ = file.split("_", maxsplit = 1)
            file_id = int(file_id)
        except ValueError:
            logger.error(f"Invalid File Resource: {file}")
            return None

        chunks = await chunk_model.get_user_chunks(
            user_id = user.user_id,
            asset_ids = [file_id],
        )

        if chunks is None:
            return None

        if not chunks:
            return []

        return await vector_db_controller.search_vector_db_collection(
            user_name = user.user_name,
            text = query,
            limit = retrieve_limit,
            chunk_ids = [
                chunk.chunk_id
                for chunk in chunks
            ],
        )

    agent_result = await chat_controller.answer_user_query(
        query = query,
        files = files or [],
        retrieve_limit = chat_request.retrieve_limit,
        search_online = chat_settings.get("search_online", False),
        file_searcher = search_file_chunks,
    )

    if agent_result is None:
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
        raise_internal_server_error()
    
    return {
        "report"              : report,
        "llm_resources"       : resources,
        "settings"            : chat_settings,
        "model_configurations": model_configurations,
    }

