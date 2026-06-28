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
from models.ip_schemas import PushChunksRequest, RetrievalRequest


# controllers
from controllers import DataController
from controllers import ProjectController
from controllers import RetrievalController

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
retrieval_router = APIRouter(
    prefix = CFG.RETRIEVAL_ROUTES_PREFIX,
    tags = ["retrieval"]
) 




@retrieval_router.post("/push/{project_name}")
async def push_chunks_into_vector_db(
    request: Request,
    project_name: str,
    push_request: PushChunksRequest
):
    # get project
    project_model = await ProjectModel.create_instance(db_client = request.app.mongodb)
    project = await project_model.get_project_or_insert_it(project_name = project_name)

    # get project chunks
    chunk_model = await ChunkModel.create_instance(db_client = request.app.mongodb)

    # database controller
    retrieval_controller = RetrievalController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
        generation_client = request.app.generation_client
    )
    retrieval_controller.create_collection(project_name, do_reset = push_request.do_reset)

    page_no = 1
    base_id = 0
    inserted_items_count = 0

    while True:
        # get page chunks
        chunks = await chunk_model.get_project_chunks(
            project_id = project.id,
            page_no = page_no,
        )

        if not chunks or len(chunks) == 0:
            break

        chunks_ids = [(base_id + chunk_id) for chunk_id in range(len(chunks))]
        
        # insert
        is_inserted = retrieval_controller.insert_into_vector_db(
            project_name = project_name,
            chunks = chunks,
            chunks_ids = chunks_ids,
        )

        if not is_inserted:
            return return_bad_request(message = ResponsesEnum.VECTOR_DB_ERROR_WHILE_INSERTION_CHUNKS.value)
        

        inserted_items_count += len(chunks)
        base_id += len(chunks)
        page_no += 1

    
    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "message": ResponsesEnum.VECTOR_DB_SUCCESS_WHILE_INSERTION_CHUNKS.value,
            "inserted_items_count": inserted_items_count
        }
    )

        
@retrieval_router.get("/get_project_collection/{project_name}")
async def get_project_collection(
    request: Request,
    project_name: str
):
    try:
        retrieval_controller = RetrievalController(
            vector_db_client = request.app.vector_db_client,
            embedding_client = request.app.embedding_client,
            generation_client = request.app.generation_client
        )

        project_collection_info = retrieval_controller.get_vector_db_collection_info(project_name = project_name)

        return JSONResponse(
            status_code = status.HTTP_200_OK,
            content = {
                "success": True,
                "project_collection_info": project_collection_info
            }
        )
    
    except Exception as e:
        return return_bad_request(
            message = (
                f"{ResponsesEnum.VECTOR_DB_GET_COLLECTION_INFO_FAILED.value}\n"
                f"Error: {e}"
            )
        )
    
@retrieval_router.post("/retrieve/{project_name}")
async def retrieve_relevant_chunks(
    project_name: str,
    request: Request,
    retrieval_request: RetrievalRequest
):
    
    retrieval_controller = RetrievalController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
        generation_client = request.app.generation_client
    )

    relevant_chunks = retrieval_controller.search_vector_db_collection(
        project_name = project_name,
        text = retrieval_request.query,
        limit = retrieval_request.limit
    )

    if not relevant_chunks:
        return return_bad_request(
            message = (
                f"{ResponsesEnum.VECTOR_DB_GET_RETRIEVAL_FAILED.value}\n"
            )
        )
    
    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "relevant_chunks": relevant_chunks
        }
    )
