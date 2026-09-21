# ------------------------------------------------------
# Implementing the routes related to the NLP workflows
# -------------------------------------------------------

# fastapi utils
from fastapi import APIRouter
from fastapi import status, Request
from fastapi.responses import JSONResponse

# models & schemas
from models.db_objects_models import UserModel
from models.db_objects_models import ChunkModel
from models.db_objects_models import AssetModel

from models.enums import ResponsesEnum, AssetTypesEnum

# from models.request_schemas import PushChunksRequest
# from models.request_schemas import RetrievalRequest
# from models.request_schemas import GenerationRequest

# controllers
from controllers import VectorDBController

# helpers
from tqdm.auto import tqdm
import helpers.config as CFG
from helpers.functional import raise_internal_server_error, return_bad_request


chat_router = APIRouter(
    prefix = CFG.CHAT_ROUTER_PATH,
    tags = ["nlp"]
)


from fastapi_core.dependecies.auth import require_authentication
from models.system_schemas import AuthContext
from fastapi import Depends
from typing import Annotated
from pydantic import BaseModel

class ChatRequest(BaseModel):
    query         : str
    retrieve_limit: int = 5,
    search_online : bool = False
    files         : list[str] = []

from models.db_schemas import User
from controllers import ChatController
from clients.llms.prompt_templates.config import LLMTasks
from helpers.config import get_settings
import json




@chat_router.post("/chat")
async def chat_will_llm(
    auth        : Annotated[AuthContext, Depends(require_authentication)],
    request     : Request,
    chat_request: ChatRequest
):
    # - setup
    vector_db_controller = VectorDBController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )

    chat_controller = ChatController(
        prompt_template_parser = request.app.prompt_template_parser
    )


    chunk_model = ChunkModel(db_client = request.app.db_client)
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
            task = LLMTasks.DOCUMENTS_SUMMARIZATION.value,
            provider = get_settings().GENERATION_BACKEND,
            documents = retrieved
        )

        
        if not chat_controller.parse_llm_response(file_information, 'need_additional_info'):
            information_resources.append(chat_controller.parse_llm_response(file_information, 'related_information'))


    # - final answer
    final_answer = await chat_controller.get_llm_response(
        query = chat_request.query,
        provider = get_settings().GENERATION_BACKEND,
        task = LLMTasks.FINAL_REPORT_GENERATION.value,
        information_resources = information_resources
    )

    return {
        'answer': final_answer
    }

