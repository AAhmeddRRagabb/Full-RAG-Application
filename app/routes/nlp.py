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
from models.ip_schemas import PushChunksRequest, RetrievalRequest, AnswerUserQueryRequest


# controllers
from controllers import DataController
from controllers import ProjectController
from controllers import NLPController

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
nlp_router = APIRouter(
    prefix = CFG.NLP_ROUTES_PREFIX,
    tags = ["nlp"]
) 


# --- Add Chunks into Vector DBs
@nlp_router.post("/push/{project_name}")
async def push_chunks_into_vector_db(
    request: Request,
    project_name: str,
    push_request: PushChunksRequest
):
    # setup
    project_model = ProjectModel(db_client = request.app.db_client)
    project_result = await project_model.get_project_or_insert_it(project_name = project_name)
    if not project_result.success:
        if project_result.error:
            logger.error(project_result.error)
        return return_bad_request(message = project_result.message)
    project = project_result.content

    chunk_model = ChunkModel(db_client = request.app.db_client)

    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )

    creation_result = await nlp_controller.create_collection(project_name, do_reset = push_request.do_reset)
    if not creation_result.success:
        logger.error(f"Error while creating collection: {creation_result.error}")
        return return_bad_request(message = creation_result.message)


    # get chunks to store
    page_no = 1
    inserted_items_count = 0

    while True:
        chunks_result = await chunk_model.get_project_chunks(
            project_id = project.project_id,
            page_no = page_no,
        )

        if not chunks_result.success:
            logger.error(f"Error while accessing project chunks: {chunks_result.error}")
            return return_bad_request(message = chunks_result.message)

        chunks = chunks_result.content
        if len(chunks) == 0 or not chunks:
            break

        chunks_ids = [chunk.chunk_id for chunk in chunks]
        
        # insert
        insertion_result = await nlp_controller.insert_into_vector_db(
            project_name = project_name,
            chunks = chunks,
            chunks_ids = chunks_ids,
        )

        if not insertion_result.success:
            logger.error(f"Error while inserting chunks: {insertion_result.error}")
            return return_bad_request(message = insertion_result.message)

        
        inserted_items_count += len(chunks)
        page_no += 1

    
    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "message": ResponsesEnum.VECTOR_DB_CHUNKS_INSERTION_SUCCESS.value,
            "inserted_items_count": inserted_items_count
        }
    )



@nlp_router.get("/get_project_collection/{project_name}")
async def get_project_collection(
    request: Request,
    project_name: str
):
    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )

    project_collection_info_result = await nlp_controller.get_vector_db_collection_info(project_name = project_name)
    if not project_collection_info_result.success:
        logger.error(f"Error Retrieving Collection Info: {project_collection_info_result.error}")
        return return_bad_request(message = project_collection_info_result.message)

    project_collection_info = project_collection_info_result.content
    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "project_collection_info": project_collection_info
        }
    )
    

# ---- Retrieve
@nlp_router.post("/retrieve/{project_name}")
async def retrieve_relevant_chunks(
    project_name: str,
    request: Request,
    retrieval_request: RetrievalRequest
):
    
    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )

    retrieval_result = await nlp_controller.search_vector_db_collection(
        project_name = project_name,
        text = retrieval_request.query,
        limit = retrieval_request.limit,
        encode_as_json = True
    )

    if not retrieval_result.success:
        logger.error(f"Error While Retrieving: {retrieval_result.error}")
        return return_bad_request(message = retrieval_result.message)

    relevant_chunks = retrieval_result.content
    if not relevant_chunks or len(relevant_chunks) == 0:
        return return_bad_request(
            message = f"{ResponsesEnum.VECTOR_DB_INNER_ERROR.value}"
        )
    
    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "relevant_chunks": relevant_chunks
        }
    )


# --- Generation 
@nlp_router.post("/answer_user_query/{project_name}")
async def retrieve_relevant_chunks(
    project_name: str,
    request: Request,
    answer_user_query_request: AnswerUserQueryRequest
):
    
    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        generation_client = request.app.generation_client,
        embedding_client = request.app.embedding_client,
        prompt_template_parser = request.app.prompt_template_parser
    )

    answer_result = await nlp_controller.answer_rag_query(
        project_name = project_name,
        query = answer_user_query_request.query,
        retrieval_limit = answer_user_query_request.limit
    )

    if not answer_result.success:
        logger.error(f"Error While Generating: {answer_result.error}")
        return return_bad_request(message = answer_result.message)

    
    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            **answer_result.content
        }
    )