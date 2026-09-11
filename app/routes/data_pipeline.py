# ------------------------------------------------------
# Implementing the routes related to the data
# -------------------------------------------------------

# fastapi utils
from fastapi import APIRouter
from fastapi import status, Request
from fastapi import File, UploadFile
from fastapi.responses import JSONResponse

# models & schemas
from models.db_objects_models import UserModel
from models.db_objects_models import ChunkModel
from models.db_objects_models import AssetModel

from models.enums import ResponsesEnum
from models.enums import AssetTypesEnum

from models.db_schemas import DataChunk, Asset
from models.request_schemas import ProcessRequest


# controllers
from controllers import UserController
from controllers import DataController
from controllers import ProcessController
from controllers import NLPController

# helpers
import helpers.config as CFG
from helpers.functional import return_bad_request, return_server_error
import os


import logging
logger = logging.getLogger("uvicorn.error")

data_pipeline_router = APIRouter(
    prefix = CFG.DATA_ROUTES_PREFIX,
    tags = ["data"]
) 



# --- Uplodaing Files
@data_pipeline_router.post("/upload/{user_name}")
async def upload_file(
    user_name: str,
    request  : Request,
    file     : UploadFile = File(...),
)-> JSONResponse:
    """
    Uploading a file to the system & saves it. This route mainly do the following:
        - validate the uploaded file
        - clean & standardize its name
        - save it within the system environment.
        - save the file as an asset in the assets collection.
        - save the user data in the users collection. 
    """
    # - setup
    data_controller = DataController()
    user_controller = UserController()

    user_model  = UserModel(db_client = request.app.db_client)
    asset_model = AssetModel(db_client = request.app.db_client)

    if not user_controller.validate_user_name(user_name = user_name):
        return return_bad_request(message = ResponsesEnum.USER_INVALID_NAME.value)
    
    user_path = user_controller.get_user_path(user_name = user_name)


    # - Process file [validate - clean]
    file_validation = data_controller.validate_uploaded_file(file = file)
    if not file_validation["valid"]:
        return return_bad_request(message = file_validation["message"])
    

    cleaned_filename = data_controller.clean_file_name(file_name = file.filename)
    file_path = os.path.join(user_path, cleaned_filename)

    user = await user_model.get_user_or_insert_it(user_name = user_name)
    if not user:
        return return_bad_request(message = ResponsesEnum.USER_INVALID_NAME.value)


    # - Check if asset already uploaded
    asset = await asset_model.get_asset(user_id = user.user_id, asset_name = cleaned_filename)
    if asset:
        return return_bad_request(message = ResponsesEnum.ASSET_ALREADY_EXISTS.value)
        

    # - Save Asset
    saved = await data_controller.save_file(file = file, file_path = file_path)
    if not saved:
        return return_server_error()


    asset = Asset(
        asset_user_id = user.user_id,
        asset_type = AssetTypesEnum.ASSET_FILE.value,
        asset_name = cleaned_filename,
        asset_size = os.path.getsize(file_path)
    )

    inserted = await asset_model.insert_asset(asset)
    if not inserted:
        return return_server_error()


    # Success state
    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "message": ResponsesEnum.FILE_UPLOADING_SUCCESS.value,
            "file_uploaded_name": asset.asset_name
        }
    )

# --------------------------- Processing Uploaded Files --------------------------------- #

@data_pipeline_router.post("/process/{user_name}")
async def process_uploaded_data(
    request        : Request,
    user_name      : str,
    process_request: ProcessRequest,
):
    """
    Processing Uploaded Files:
        >> Delete previous chunks if required
        >> Choose whetehr to chunk a specific files or all user files
        >> Chunking & Save Chunks
    """
    # - Setup
    user_model = UserModel(db_client = request.app.db_client)
    chunk_model = ChunkModel(db_client = request.app.db_client)
    asset_model = AssetModel(db_client = request.app.db_client)

    process_controller = ProcessController(user_name = str(user_name))

    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )


    user = await user_model.get_user_by_name(user_name)
    if not user:
        return return_bad_request(message = ResponsesEnum.USER_NOT_FOUND.value)


    # - Resetting [if required]
    if process_request.do_reset:
        deleted = await chunk_model.delete_user_chunks(user_id = user.user_id)
        if not deleted:
            return return_server_error()


        # delete vectors
        deleted = await nlp_controller.delete_collection(user_name)
        if not deleted:
            return return_server_error()


    # - Get assets to chunk
    if process_request.file_name:
        asset = await asset_model.get_asset(user_id = user.user_id, asset_name = process_request.file_name)
        if not asset:
            return return_bad_request(message = ResponsesEnum.ASSET_INVALID_NAME.value)
        
        user_files_ids = {asset.asset_id : asset.asset_name}


    else:
        assets = await asset_model.get_user_assets(user_id = user.user_id, asset_type = AssetTypesEnum.ASSET_FILE.value)
        if len(assets) == 0 or not assets:
            return return_bad_request(message = ResponsesEnum.ASSETs_NOT_FOUND.value)

        user_files_ids = {record.asset_id : record.asset_name for record in assets}


    # - Chunking
    no_records_inserted = 0
    no_processed_files = 0
    for asset_id, asset_name in user_files_ids.items():
        has_chunks = await chunk_model.has_asset_chunks(user_id = user.user_id, asset_id = asset_id)

        if has_chunks:
            logger.info(f"Asset already chunked: {asset_name}.")
            if process_request.file_name:
                break

            continue


        file_content = process_controller.get_file_content(file_id = asset_name)
        if file_content is None:
            logger.error(f"Error while loading file: {asset_name}. File Content: {file_content}")
            continue

        chunks = process_controller.get_chunks(
            file_content = file_content,
            chunk_size = process_request.chunk_size,
            overlap_size = process_request.overlap_size
        )
  
        if not chunks or len(chunks) == 0:
            logger.error(f"Error while chunking file: {asset_name}. Chunks: {chunks}")
            continue
    

        chunk_objects = [
            DataChunk(
                chunk_text = chunk.page_content,
                chunk_name = f"{asset_name}_chunk_{i + 1}",
                chunk_user_id = user.user_id,
                chunk_metadata = chunk.metadata,
                chunk_asset_id = asset_id,
                chunk_order = i + 1,
            )
            for i, chunk in enumerate(chunks)
        ]

        inserted = await chunk_model.insert_many_chunks(chunk_objects)
        if not inserted:
            continue

        no_records_inserted += len(chunk_objects)
        no_processed_files += 1


    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            'message': ResponsesEnum.FILE_PROCESSING_SUCCESS.value,
            "no_chunks_inserted": no_records_inserted,
            "no_processed_files": no_processed_files
        }
    )
