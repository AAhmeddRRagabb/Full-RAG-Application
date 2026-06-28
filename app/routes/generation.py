# fastapi utils
from fastapi import APIRouter
from fastapi import status, Request
from fastapi import File, UploadFile
from fastapi.responses import JSONResponse

# models & schemas
from models.db_objects_models import ProjectModel
from models.db_objects_models import ChunkModel
from models.db_objects_models import AssetModel

from models.enums import ResponsesEnum
from models.enums import AssetTypesEnum

from models.db_schemas import DataChunk, Asset
from models.ip_schemas import PushChunksRequest, AnswerUserQueryRequest


# controllers
from controllers import DataController
from controllers import ProjectController
from controllers import GenerationController

# helpers
import aiofiles
import helpers.config as CFG
import os


import logging
logger = logging.getLogger("uvicorn.error")

# ------------------------------------ Utils ---------------------------------
def return_bad_request(message: str) -> JSONResponse:
    return JSONResponse(
        status_code = status.HTTP_400_BAD_REQUEST,
        content = {
            "success": False,
            "message": message
        }
    )



# ------------------------------------ Routers ---------------------------------
generation_router = APIRouter(
    prefix = CFG.GENERATION_ROUTES_PREFIX,
    tags = ["generation"]
) 


@generation_router.post("/answer_user_query/{project_name}")
async def retrieve_relevant_chunks(
    project_name: str,
    request: Request,
    answer_user_query_request: AnswerUserQueryRequest
):
    
    generation_controller = GenerationController(
        vector_db_client = request.app.vector_db_client,
        generation_client = request.app.generation_client,
        embedding_client = request.app.embedding_client,
        prompt_template_parser = request.app.prompt_template_parser
    )

    results = generation_controller.answer_rag_query(
        project_name = project_name,
        query = answer_user_query_request.query,
        limit = answer_user_query_request.limit
    )

    if not results:
        return return_bad_request(
            message = (
                f"{ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value}\n"
            )
        )
    
    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            **results
        }
    )
