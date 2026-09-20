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
from controllers import NLPController

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
@chat_router.post("/chat")
async def chat_will_llm(
    auth: Annotated[AuthContext, Depends(require_authentication)],
    request: Request,
    chat_request: ChatRequest
):
    # - setup
    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        generation_client = request.app.generation_client,
        embedding_client = request.app.embedding_client,
        prompt_template_parser = request.app.prompt_template_parser
    )
    chunk_model = ChunkModel(db_client = request.app.db_client)
    
    user: User = auth.user

    from pprint import pprint

    search_online = chat_request.search_online
    files_to_retrieve_from = chat_request.files

    # - search only in required files
    file_ids = [int(file_id) for file_id in files_to_retrieve_from]
    chunks = await chunk_model.get_user_chunks(
        user_id = user.user_id,
        asset_ids = file_ids,
    )

    chunk_ids = [c.chunk_id for c in chunks]

    retrieved = await nlp_controller.search_vector_db_collection(
        user_name = user.user_name,
        text = chat_request.query,
        limit = chat_request.retrieve_limit,
        chunk_ids = chunk_ids
    )

    formatted_doc = nlp_controller.format_retrieved_documents(retrieved)
    result = await nlp_controller.answer_rag_query(
        query = chat_request.query,
        formatted_documents = formatted_doc
    )

    pprint(result)

    return {
        'answer': result['answer']
    }

