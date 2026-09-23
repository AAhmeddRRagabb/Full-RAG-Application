# ------------------------------------------------------
# Implementing the routes related to the NLP workflows
# -------------------------------------------------------


# utils
import helpers.config as CFG
from helpers.functional import raise_internal_server_error, return_bad_request
from typing import Annotated
from pydantic import BaseModel
from helpers.config import get_settings


# controllers
from controllers import VectorDBController
from controllers import ChatController

# fastapi utils
from fastapi import APIRouter, Depends
from fastapi import status, Request
from fastapi.responses import JSONResponse

# models & schemas
from models.db_objects_models import ChunkModel
from models.system_schemas import AuthContext
from models.db_schemas import User


# clients
from clients.llms.config import AgentTasks
from clients.vector_dbs.vector_db_clients import PGVectorVDBClient
from clients.llms.llm_clients import HuggingfaceLLMClient, GoogleLLMClient, GroqLLMClient
from clients.llms.prompt_templates import PromptTemplateParser
from sqlalchemy.ext.asyncio import AsyncSession

# dependecies
from app_core.dependecies.auth import require_authentication
from app_core.dependecies.clients import (
    get_embedding_client, 
    get_vector_db_client, 
    get_prompt_template_parser, 
    get_llm_clients,
    get_db_client
)



chat_router = APIRouter(
    prefix = CFG.CHAT_ROUTER_PATH,
    tags = ["nlp"]
)



class ChatRequest(BaseModel):
    query         : str
    retrieve_limit: int = 5,
    search_online : bool = False
    files         : list[str] = []



@chat_router.post("/chat")
async def chat_will_llm(
    auth                  : Annotated[AuthContext, Depends(require_authentication)],
    db_client             : Annotated[AsyncSession, Depends(get_db_client)],
    vector_db_client      : Annotated[PGVectorVDBClient, Depends(get_vector_db_client)],
    embedding_client      : Annotated[HuggingfaceLLMClient | GoogleLLMClient, Depends(get_embedding_client)],
    llm_clients           : Annotated[dict[str, HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient], Depends(get_llm_clients)],
    prompt_template_parser: Annotated[PromptTemplateParser, Depends(get_prompt_template_parser)],
    chat_request          : ChatRequest
):
    # - setup
    vector_db_controller = VectorDBController(
        vector_db_client = vector_db_client,
        embedding_client = embedding_client,
    )

    chat_controller = ChatController(
        prompt_template_parser = prompt_template_parser,
        llm_clients = llm_clients
    )

    chunk_model = ChunkModel(db_client = db_client)
    user: User = auth.user

    search_online = chat_request.search_online
    files_to_retrieve_from = chat_request.files


    # - search only in required files
    file_ids = [int(file_id) for file_id in files_to_retrieve_from]
    information_resources = []

    for file_id in file_ids:
        chunks = await chunk_model.get_user_chunks(
            user_id = user.user_id,
            asset_ids = [file_id],
        )

        chunk_ids = [c.chunk_id for c in chunks]
        retrieved = await vector_db_controller.search_vector_db_collection(
            user_name = user.user_name,
            text = chat_request.query,
            limit = chat_request.retrieve_limit,
            chunk_ids = chunk_ids
        )

        
        file_information = await chat_controller.get_llm_response(
            query = chat_request.query,
            task = AgentTasks.FI.value,
            provider = get_settings().GENERATION_BACKEND,
            documents = retrieved
        )

        
        if not chat_controller.parse_llm_response(file_information, 'need_additional_info'):
            information_resources.append(chat_controller.parse_llm_response(file_information, 'related_information'))


    # - final answer
    final_answer = await chat_controller.get_llm_response(
        query = chat_request.query,
        provider = get_settings().GENERATION_BACKEND,
        task = AgentTasks.RG.value,
        information_resources = information_resources
    )

    return {
        'answer': final_answer
    }

