# ------------------------------------------------------
# User data routes
# ------------------------------------------------------

# utils
from helpers.config import get_settings
from sqlalchemy.orm import sessionmaker

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

engine = create_async_engine(get_settings().DATABASE_URL)

local_db_client = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


import os
from typing import Annotated
import logging
import helpers.config as CFG
logger = logging.getLogger("uvicorn.error")

from helpers.functional import log_title, raise_internal_server_error

# fastapi
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks
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



async def process_uploaded_file(
    *,
    user_id  : int,
    user_name: str,
    user_uuid: str,
    asset_id : int,
    cleaned_filename: str,
    vector_db_client: PGVectorVDBClient,
    embedding_client: HuggingfaceLLMClient | GoogleLLMClient,
) -> None:
    """
    Runs after the upload response has already been sent.
    """

    try:
        log_title(f"Background File Processing: {cleaned_filename}")

        data_controller = DataController(user_key = user_uuid)

        vector_db_controller = VectorDBController(
            vector_db_client = vector_db_client,
            embedding_client = embedding_client,
        )

        chunk_model = ChunkModel(db_client = local_db_client)

        # - Chunking File
        file_content = data_controller.get_file_content(cleaned_filename)

        if file_content is None:
            logger.error(f"Error while loading file: {cleaned_filename}. File Content: {file_content}")
            return

            
        chunks = data_controller.get_chunks(file_content = file_content)

        if not chunks:
            logger.error(f"Error while chunking file: {cleaned_filename}. Chunks: {chunks}")
            return

        chunk_objects = [
            DataChunk(
                chunk_text = chunk.page_content,
                user_id = user_id,
                chunk_metadata = chunk.metadata,
                asset_id = asset_id,
            )
            for chunk in chunks
        ]

        
        if not await chunk_model.insert_many_chunks(chunk_objects):
            logger.error(f"Could not save chunks: {cleaned_filename}")
            return

        logger.info(
            f">> File Chunked Successfully. "
            f"User: {user_name}. No.Chunks: {len(chunk_objects)}"
        )

        # - embed & save the file in V-DB
        if not await vector_db_controller.create_collection(user_key = user_uuid):
            logger.error(f"Could not create vector collection for: {user_name}")
            return

        chunk_ids = [chunk.chunk_id for chunk in chunk_objects]

        if not await vector_db_controller.insert_chunks_into_vector_db(
            user_key = user_uuid,
            chunks = chunk_objects,
            chunks_ids = chunk_ids,
        ):
            logger.error(f"Could not insert vectors for file: {cleaned_filename}")
            return

        logger.info(
            f">> File Embedded Successfully. "
            f"User: {user_name}. "
            f"Collection: {vector_db_controller.get_collection_name(user_name)}"
        )

    except Exception:
        logger.exception(f"Background processing failed for file: {cleaned_filename}")


@data_router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
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
    user: User = auth.user

    # - setup
    data_controller = DataController(user_key = user.user_uuid)
    user_controller = UserController()
    
    asset_model = AssetModel(db_client = db_client)
    user_path = user_controller.get_user_path(user_key = user.user_uuid)


    # - process file [validate - clean]
    file_validation = data_controller.validate_uploaded_file(file = file)
    if not file_validation["valid"]:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = file_validation['message']
        )
    

    cleaned_filename = data_controller.clean_filename(filename = file.filename)
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
        user_id = user.user_id,
        asset_type = AssetTypesEnum.ASSET_FILE.value,
        asset_name = cleaned_filename,
        asset_metadata = {
            "size": os.path.getsize(file_path),
        },
    )

    if not await asset_model.insert_asset(asset):
        raise raise_internal_server_error()

    background_tasks.add_task(
        process_uploaded_file,
        user_name = user.user_name,
        user_id = user.user_id,
        user_uuid = user.user_uuid,
        asset_id = asset.asset_id,
        cleaned_filename = cleaned_filename,
        vector_db_client = vector_db_client,
        embedding_client = embedding_client,
    )

    return {
        "message": "File uploaded successfully and is being processed.",
        "filename": asset.asset_name,
        "status": "processing",
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
            "file_id" : file.asset_id,
            "filename": file.asset_name
        } for file in user_files
    ]


    return {
        "user_files": user_files
    }


@data_router.delete("/files/{asset_id}")
async def delete_user_file(
    asset_id        : int,
    auth            : Annotated[AuthContext, Depends(require_authentication)],
    db_client       : Annotated[AsyncSession, Depends(get_db_client)],
    vector_db_client: Annotated[PGVectorVDBClient, Depends(get_vector_db_client)],
    embedding_client: Annotated[HuggingfaceLLMClient | GoogleLLMClient, Depends(get_embedding_client)],
):
    user: User = auth.user
    user_key = user.user_uuid

    asset_model = AssetModel(db_client = db_client)
    chunk_model = ChunkModel(db_client = db_client)
    vector_db_controller = VectorDBController(
        vector_db_client = vector_db_client,
        embedding_client = embedding_client,
    )

    asset = await asset_model.get_user_asset(
        user_id = user.user_id,
        asset_id = asset_id,
    )

    if asset is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "File not found",
        )

    chunk_ids = await chunk_model.get_asset_chunk_ids(
        user_id = user.user_id,
        asset_id = asset.asset_id,
    )

    if chunk_ids is None:
        raise raise_internal_server_error()

    if chunk_ids and not await vector_db_controller.delete_chunks_from_vector_db(
        user_key = user_key,
        chunk_ids = chunk_ids,
    ):
        raise raise_internal_server_error()

    if not await chunk_model.delete_asset_chunks(
        user_id = user.user_id,
        asset_id = asset.asset_id,
    ):
        raise raise_internal_server_error()

    if not await asset_model.delete_asset(
        user_id = user.user_id,
        asset_id = asset.asset_id,
    ):
        raise raise_internal_server_error()

    file_path = os.path.join(UserController().get_user_path(user_key = user_key), asset.asset_name)
    if os.path.exists(file_path):
        os.remove(file_path)

    return {
        "message": "File deleted successfully",
    }