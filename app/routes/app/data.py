import asyncio
import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from clients.llms.llm_clients import GoogleLLMClient, HuggingfaceLLMClient
from clients.vector_dbs.vector_db_clients import PGVectorVDBClient
from controllers import DataController, UserController, VectorDBController
from core.dependecies.auth import require_authentication, require_csrf
from core.dependecies.clients import get_db_client, get_embedding_client, get_vector_db_client
from core.helpers import raise_internal_server_error
from core.system_settings import DATA_ROUTES_PATH
from models.db_models import AssetModel, ChunkModel
from models.db_schemas import Asset, DataChunk
from models.db_schemas.redis_data import AuthContext
from models.enums import AssetTypesEnum, ResponsesEnum


logger = logging.getLogger("uvicorn.error")
data_router = APIRouter(prefix=DATA_ROUTES_PATH, tags=["files"])


@data_router.post("/upload")
async def upload_file(
    auth: Annotated[AuthContext, Depends(require_csrf)],
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
    vector_db_client: Annotated[PGVectorVDBClient, Depends(get_vector_db_client)],
    embedding_client: Annotated[HuggingfaceLLMClient | GoogleLLMClient, Depends(get_embedding_client)],
    file: UploadFile = File(...),
):
    user = auth.user
    data = DataController(user_key=user.user_uuid)
    assets = AssetModel(db_client)
    chunks = ChunkModel(db_client)
    vectors = VectorDBController(vector_db_client, embedding_client)

    validation = data.validate_uploaded_file(file)
    if not validation["valid"]:
        raise HTTPException(400, validation["message"])

    name = data.clean_filename(file.filename)
    existing = await assets.get_asset(user.user_id, name)
    if existing:
        return {"file_id": existing.asset_id, "filename": name, "message": "PDF already uploaded."}

    path = os.path.join(UserController().get_user_path(user.user_uuid), name)
    if not await data.save_file(file, path):
        if os.path.exists(path):
            os.remove(path)
        raise_internal_server_error()

    asset = Asset(
        user_id=user.user_id,
        asset_name=name,
        asset_type=AssetTypesEnum.ASSET_FILE.value,
        asset_status="processing",
        asset_metadata={"size": os.path.getsize(path)},
    )
    if not await assets.insert_asset(asset):
        os.remove(path)
        raise_internal_server_error()

    chunk_ids = []
    try:
        pages = await asyncio.to_thread(data.get_file_content, name)
        parts = await asyncio.to_thread(data.get_chunks, pages) if pages else None
        if not parts:
            raise RuntimeError("PDF contains no readable text")

        records = [
            DataChunk(
                user_id=user.user_id,
                asset_id=asset.asset_id,
                chunk_text=part.page_content,
                chunk_metadata=part.metadata,
            )
            for part in parts
        ]
        if not await chunks.insert_many_chunks(records):
            raise RuntimeError("Could not save PDF chunks")
        chunk_ids = [record.chunk_id for record in records]
        if not await vectors.create_collection(user.user_uuid):
            raise RuntimeError("Could not create vector collection")
        if not await vectors.insert_chunks_into_vector_db(user.user_uuid, records, chunk_ids):
            raise RuntimeError("Could not index PDF")
        if not await assets.update_asset_status(user.user_id, asset.asset_id, "ready"):
            raise RuntimeError("Could not finish PDF upload")
    except Exception as error:
        logger.exception("PDF upload failed")
        if chunk_ids:
            await vectors.delete_chunks_from_vector_db(user.user_uuid, chunk_ids)
        await chunks.delete_asset_chunks(user.user_id, asset.asset_id)
        await assets.delete_asset(user.user_id, asset.asset_id)
        if os.path.exists(path):
            os.remove(path)
        if str(error) == "PDF contains no readable text":
            raise HTTPException(400, "This PDF has no readable text. Upload a text-based PDF.")
        raise_internal_server_error()

    return {"file_id": asset.asset_id, "filename": name, "message": "PDF ready to use."}


@data_router.get("/get_user_files")
async def get_user_files(
    auth: Annotated[AuthContext, Depends(require_authentication)],
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
):
    files = await AssetModel(db_client).get_user_assets(auth.user.user_id, AssetTypesEnum.ASSET_FILE.value)
    if files is None:
        raise_internal_server_error()
    return {
        "user_files": [
            {"file_id": file.asset_id, "filename": file.asset_name}
            for file in files
            if file.asset_name.lower().endswith(".pdf")
        ]
    }


@data_router.delete("/files/{asset_id}")
async def delete_user_file(
    asset_id: int,
    auth: Annotated[AuthContext, Depends(require_csrf)],
    db_client: Annotated[AsyncSession, Depends(get_db_client)],
    vector_db_client: Annotated[PGVectorVDBClient, Depends(get_vector_db_client)],
    embedding_client: Annotated[HuggingfaceLLMClient | GoogleLLMClient, Depends(get_embedding_client)],
):
    user = auth.user
    assets = AssetModel(db_client)
    chunks = ChunkModel(db_client)
    vectors = VectorDBController(vector_db_client, embedding_client)
    asset = await assets.get_user_asset(user.user_id, asset_id)
    if asset is None:
        raise HTTPException(404, ResponsesEnum.FILE_NOT_FOUND.value)

    chunk_ids = await chunks.get_asset_chunk_ids(user.user_id, asset_id)
    if chunk_ids is None:
        raise_internal_server_error()
    if chunk_ids and not await vectors.delete_chunks_from_vector_db(user.user_uuid, chunk_ids):
        raise_internal_server_error()
    if not await chunks.delete_asset_chunks(user.user_id, asset_id):
        raise_internal_server_error()
    if not await assets.delete_asset(user.user_id, asset_id):
        raise_internal_server_error()

    path = os.path.join(UserController().get_user_path(user.user_uuid), asset.asset_name)
    if os.path.exists(path):
        os.remove(path)
    return {"message": ResponsesEnum.FILE_DELETED_SUCCESSFULLY.value}
