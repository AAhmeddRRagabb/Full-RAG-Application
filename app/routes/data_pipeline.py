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
from helpers.functional import parse_component_result, FAILURE, return_bad_request
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
    request: Request,
    file: UploadFile = File(...),
)-> JSONResponse:
    """
    Uploading a file to the system & saves it. This route mainly do the following:
        - validate the uploaded file
        - clean & standardize its name
        - save it within the system environment.
        - save the file as an asset in the assets collection.
        - save the user data in the users collection. 
    """
    # Setup
    data_controller = DataController()
    user_controller = UserController()

    user_model  = UserModel(db_client = request.app.db_client)
    asset_model = AssetModel(db_client = request.app.db_client)


    flag, valid_or_failure = parse_component_result(user_controller.validate_user_name(user_name = user_name))
    if flag == FAILURE:
        return valid_or_failure
    
    user_path = user_controller.get_user_path(user_name = user_name)


    # - Process file [validate - clean]
    flag, validated_or_failure = parse_component_result(data_controller.validate_uploaded_file(file = file))
    if flag == FAILURE:
        return validated_or_failure

    cleaned_filename = data_controller.clean_file_name(file_name = file.filename).content
    file_path = os.path.join(user_path, cleaned_filename)

    flag, user_or_failure = parse_component_result(await user_model.get_user_or_insert_it(user_name = user_name), error_message = "Error while accessing the user")
    if flag == FAILURE:
        return user_or_failure


    # - Check if asset already uploaded
    flag, asset_or_failure = parse_component_result(
        await asset_model.get_asset_record(user_id = user_or_failure.user_id, asset_name = cleaned_filename),
        error_message = 'Error while accessing asset'
    )
    if flag == FAILURE:
        return asset_or_failure 

    if asset_or_failure: # does exist
        return return_bad_request(message = ResponsesEnum.ASSET_ALREADY_EXISTS.value)


    # Save Asset
    flag, valid_or_failure = parse_component_result(await data_controller.save_file(file = file, file_path = file_path), error_message = 'Error while saving the file')
    if flag == FAILURE:
        return valid_or_failure


    asset = Asset(
        asset_user_id = user_or_failure.user_id,
        asset_type = AssetTypesEnum.ASSET_FILE.value,
        asset_name = cleaned_filename,
        asset_size = os.path.getsize(file_path)
    )

    flag, asset_or_failure = parse_component_result(await asset_model.create_asset(asset), error_message = 'Error while saving the asset')
    if flag == FAILURE:
        return asset_or_failure


    # Success state
    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "message": ResponsesEnum.FILE_UPLOADING_SUCCESS.value,
            "file_uploaded_name": asset_or_failure.asset_name
        }
    )


# Processing Files
@data_pipeline_router.post("/process/{user_name}")
async def process_uploaded_data(
    request: Request,
    user_name: str,
    process_request: ProcessRequest,
):
    """
    Processing Uploaded Files:
        >> Delete previous chunks if required
        >> Choose whetehr to chunk a specific files or all user files
        >> Chunking & Save Chunks
    """
    # Setup
    user_model = UserModel(db_client = request.app.db_client)
    chunk_model = ChunkModel(db_client = request.app.db_client)
    asset_model = AssetModel(db_client = request.app.db_client)

    process_controller = ProcessController(user_name = str(user_name))

    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )


    flag, user_or_failure = parse_component_result(await user_model.get_user(user_name), 'Error while accessing the user')
    if flag == FAILURE:
        return user_or_failure

    if not user_or_failure:
        return return_bad_request(message = ResponsesEnum.USER_NOT_FOUND.value)
    

    # Resetting [if required]
    if process_request.do_reset:
        flag, n_deleted_or_failure = parse_component_result(
            result = await chunk_model.delete_chunks_by_user_id(user_id = user_or_failure.user_id),
            error_message = 'Error while deleting chunks'
        )
        if flag == FAILURE:
            return n_deleted_or_failure


        # delete vectors
        flag, deleted_or_failure = parse_component_result(
            result = await nlp_controller.delete_collection(user_name),
            error_message = 'Error while deleting vectors'
        )
        if flag == FAILURE:
            return deleted_or_failure



    # Get assets to chunk
    if process_request.file_name:
        flag, asset_or_failure = parse_component_result(
            result = await asset_model.get_asset_record(user_id = user_or_failure.user_id, asset_name = process_request.file_name),
            error_message = 'Error while accessing asset'
        )

        if flag == FAILURE:
            return asset_or_failure

        if not asset_or_failure:
            return return_bad_request(message = ResponsesEnum.ASSET_INVALID_NAME.value)
        
        
        user_files_ids = {asset_or_failure.asset_id : asset_or_failure.asset_name}

    else:
        flag, assets_or_failure = parse_component_result(
            result = await asset_model.get_all_user_assets(user_id = user_or_failure.user_id, asset_type = AssetTypesEnum.ASSET_FILE.value),
            error_message = 'Error while accessing assets'
        )

        if flag == FAILURE:
            return assets_or_failure

        if len(assets_or_failure) == 0 or not assets_or_failure:
            return return_bad_request(message = ResponsesEnum.ASSET_NOT_FOUND.value)

        user_files_ids = {record.asset_id : record.asset_name for record in assets_or_failure}


    # Chunking
    no_records_inserted = 0
    no_processed_files = 0
    for asset_id, asset_name in user_files_ids.items():
        flag, has_chunks_or_failure = parse_component_result(
            await chunk_model.has_asset_chunks(user_id = user_or_failure.user_id, asset_id = asset_id), 
            error_message = 'Error while accessing chunks'
        )

        if flag == FAILURE:
            return has_chunks_or_failure

        if has_chunks_or_failure:
            logger.info(f"Asset already chunked: {asset_name}.")
            if process_request.file_name:
                break

            continue


        file_content = process_controller.get_file_content(file_id = asset_name)
        if file_content is None:
            logger.error(f"Error while loading file: {asset_name}. File Content: {file_content}")
            continue

        flag, chunks_or_failure = parse_component_result(
            result = process_controller.get_chunks(
                file_content = file_content,
                chunk_size = process_request.chunk_size,
                overlap_size = process_request.overlap_size,
            ), error_message = 'Error while chunking file'
        )

        if flag == FAILURE:
            continue

  
        if not chunks_or_failure or len(chunks_or_failure) == 0:
            logger.error(f"Error while chunking file: {asset_name}. Chunks: {chunks_or_failure}")
            continue
    

        
        chunk_objects = [
            DataChunk(
                chunk_text = chunk.page_content,
                chunk_name = f"{asset_name}_chunk_{i + 1}",
                chunk_user_id = user_or_failure.user_id,
                chunk_metadata = chunk.metadata,
                chunk_asset_id = asset_id,
                chunk_order = i + 1,
            )
            for i, chunk in enumerate(chunks_or_failure)
        ]

        flag, n_inserted_or_failure = parse_component_result(
            result = await chunk_model.insert_many_chunks(chunk_objects),
            error_message = 'Error while saving chunk'
        )
        if flag == FAILURE:
            continue

        
        no_records_inserted += n_inserted_or_failure
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
