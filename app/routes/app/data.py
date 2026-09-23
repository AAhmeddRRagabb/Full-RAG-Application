# ------------------------------------------------------
# User data routes
# ------------------------------------------------------

# utils
import os
from typing import Annotated
import logging
import helpers.config as CFG
logger = logging.getLogger("uvicorn.error")

from helpers.functional import log_title, raise_internal_server_error

# fastapi
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from app_core.dependecies.auth import require_authentication
from app_core.dependecies.clients import get_db_client, get_embedding_client, get_vector_db_client


# clients
from clients.llms.llm_clients import HuggingfaceLLMClient, GoogleLLMClient
from clients.vector_dbs.vector_db_clients import PGVectorVDBClient
from sqlalchemy.ext.asyncio import AsyncSession

# controllers
from controllers import DataController
from controllers import VectorDBController
from controllers import UserController

# models
from models.db_objects_models import AssetModel, ChunkModel
from models.db_schemas import Asset, DataChunk, User
from models.enums import AssetTypesEnum, ResponsesEnum
from models.system_schemas import AuthContext


data_router = APIRouter(
    prefix = CFG.DATA_ROUTES_PATH,
    tags = ["data"]
) 



@data_router.post("/upload")
async def upload_file(
    auth            : Annotated[AuthContext, Depends(require_authentication)],
    db_client       : Annotated[AsyncSession, Depends(get_db_client)],
    vector_db_client: Annotated[PGVectorVDBClient, Depends(get_vector_db_client)],
    embedding_client: Annotated[HuggingfaceLLMClient | GoogleLLMClient, Depends(get_embedding_client)],
    file            : UploadFile = File(...),
) -> dict:
    """
    Upload a file and prepare its chunks for retrieval.
        - validate the uploaded file
        - clean & standardize its name
        - save it within the system environment.
        - save the file as an asset in the assets collection.
        - save the user data in the users collection.
        - chunk the file & saving its chunks. 
    """
    log_title("Uploading File")

    # - setup
    data_controller = DataController()
    user_controller = UserController()
    
    vector_db_controller  = VectorDBController(
        vector_db_client = vector_db_client,
        embedding_client = embedding_client
    )

    asset_model = AssetModel(db_client = db_client)
    chunk_model = ChunkModel(db_client = db_client)

    user: User = auth.user
    user_path = user_controller.get_user_path(user_name = user.user_name)
    data_controller = DataController(user_name = user.user_name)


    # - process file [validate - clean]
    file_validation = data_controller.validate_uploaded_file(file = file)
    if not file_validation["valid"]:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = file_validation['message']
        )
    

    cleaned_filename = data_controller.clean_file_name(file_name = file.filename)
    file_path = os.path.join(user_path, cleaned_filename)


    # - check if asset already uploaded
    asset = await asset_model.get_asset(user_id = user.user_id, asset_name = cleaned_filename)
    if asset:
        return {
            "success": True,
            "message": ResponsesEnum.FILE_UPLOADING_SUCCESS.value
        }
        

    # - save Asset
    saved = await data_controller.save_file(file = file, file_path = file_path)
    if not saved:
        raise raise_internal_server_error()


    asset = Asset(
        asset_user_id = user.user_id,
        asset_type = AssetTypesEnum.ASSET_FILE.value,
        asset_name = cleaned_filename,
        asset_size = os.path.getsize(file_path)
    )

    inserted = await asset_model.insert_asset(asset)
    if not inserted:
        raise raise_internal_server_error()

    logger.info(f">> File Uploaded Successfully. User: {user.user_name}. File: {cleaned_filename}")


    # - chunk file
    file_content = data_controller.get_file_content(file_id = cleaned_filename)
    if file_content is None:
        logger.error(f"Error while loading file: {cleaned_filename}. File Content: {file_content}")
        raise raise_internal_server_error()


    chunks = data_controller.get_chunks(file_content = file_content)
    if not chunks or len(chunks) == 0:
        logger.error(f"Error while chunking file: {cleaned_filename}. Chunks: {chunks}")
        raise raise_internal_server_error()

    chunk_objects = [
        DataChunk(
            chunk_text     = chunk.page_content,
            chunk_name     = f"{cleaned_filename}_chunk_{i + 1}",
            chunk_user_id  = user.user_id,
            chunk_metadata = chunk.metadata,
            chunk_asset_id = asset.asset_id,
            chunk_order    = i + 1,
        )
        for i, chunk in enumerate(chunks)
    ]

    inserted = await chunk_model.insert_many_chunks(chunk_objects)
    if not inserted:
        raise_internal_server_error()

    logger.info(f">> File Chunked Successfully. User: {user.user_name}. No.Chunks: {len(chunk_objects)}")


    # - embed & save the file in V-DB
    if not await vector_db_controller.create_collection(user.user_name):
        raise raise_internal_server_error()


    chunks_ids = [chunk.chunk_id for chunk in chunk_objects]
    if not await vector_db_controller.insert_chunks_into_vector_db(
        user_name = user.user_name,
        chunks = chunk_objects,
        chunks_ids = chunks_ids,
    ):
        raise raise_internal_server_error()

    logger.info(f">> File Embeded Successfully. User: {user.user_name}. CollectionName: {vector_db_controller.get_collection_name(user.user_name)}")
    

    # Success state
    log_title("File Uploaded Successfully")
    return {
        "message"       : ResponsesEnum.FILE_UPLOADING_SUCCESS.value,
        "filename"      : asset.asset_name,
        "no_file_chunks": len(chunk_objects)
    }
    



@data_router.get("/get_user_files")
async def get_user_files(
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
    auth     : Annotated[AuthContext, Depends(require_authentication)]
):
    user: User = auth.user
    asset_model = AssetModel(db_client = db_client)

    user_files = await asset_model.get_user_assets(
        user_id = user.user_id,
        asset_type = AssetTypesEnum.ASSET_FILE.value
    )

    if not user_files:
        return {
            "user_files": []
        }

    user_files = [
        {
            "file_id"  : file.asset_id,
            "file_name": file.asset_name
        } for file in user_files
    ]


    return {
        "user_files": user_files
    }
