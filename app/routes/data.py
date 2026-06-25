# ------------------------------------------------------
# Implementing the routes related to the data
# ------------------------------------------------------
# ----------------------------------- Dependecies ---------------------------------
# fastapi utils
from fastapi import APIRouter, Depends
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
from models.ip_schemas import ProcessRequest


# controllers
from controllers import DataController
from controllers import ProjectController
from controllers import ProcessController

# helpers
import aiofiles
import helpers.config as CFG
import os
from helpers.functional import print_error_message

import logging
logger = logging.getLogger("uvicorn.error")
# ---------------------------------- Utils Funcs ---------------------------
def return_bad_request(message: str) -> JSONResponse:
    return JSONResponse(
        status_code = status.HTTP_400_BAD_REQUEST,
        content = {
            "success": False,
            "message": message
        }
    )


# ------------------------------------ Routers ---------------------------------
data_router = APIRouter(
    prefix = CFG.DATA_ROUTES_PREFIX,
    tags = ["data"]
) 



@data_router.post("/upload/{project_name}")
async def upload_file(
    project_name: str,
    request: Request,
    file: UploadFile = File(...),
)-> JSONResponse:
    """
    Uploading a file to the system & saves it. This route mainly do the following:
        - validate the uploaded file
        - clean & standardize its name
        - save it within the system environment.
        - save the file as an asset in the assets collection.
        - save the project data in the projects collection. 
    """
    # init collection models & controllers
    project_model = await ProjectModel.create_instance(db_client = request.app.mongodb)
    asset_model = await AssetModel.create_instance(db_client = request.app.mongodb)

    data_controller = DataController()
    project_path = ProjectController().get_project_path(project_name = project_name)


    # processing file [validate -> clean name -> save]
    validation_results = data_controller.validate_uploaded_file(file = file)
    if validation_results['status'] == "error":
        return return_bad_request(message = validation_results['message'])
  

    cleaned_filename = data_controller.clean_file_name(file_name = file.filename)
    file_path = os.path.join(project_path, cleaned_filename)

    try:
        async with aiofiles.open(file = file_path, mode = 'wb') as f:
            while chunk := await file.read(size = CFG.FILE_CHUNK_SIZE_B):
                await f.write(chunk)

    except Exception as e:
        logger.error(f"Error while uploading a file: {e}")
        return return_bad_request(message = ResponsesEnum.FILE_UPLOADED_FAILED.value)
    
    # save in mongo_db
    project = await project_model.get_project_or_insert_it(project_name = project_name)
    asset = Asset(
        asset_project_id = project.id,
        asset_type = AssetTypesEnum.ASSET_FILE.value,
        asset_name = cleaned_filename,
        asset_size = os.path.getsize(file_path)
    )
    asset_record = await asset_model.create_asset(asset)

    # return on success
    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "message": ResponsesEnum.FILE_UPLOADED_SUCCESSFULLY.value,
            "file_uploaded_name": asset_record.asset_name
        }
    )



@data_router.post("/process/{project_name}")
async def process_uploaded_data(
    request: Request,
    project_name: str,
    process_request: ProcessRequest,
):
    """
    Processing Uploaded Files:
        >> Delete previous chunks if required
        >> Choose whetehr to chunk a specific files or all project files
        >> Chunking & Save Chunks
    """
    # init collection models & controllers
    project_model = await ProjectModel.create_instance(db_client = request.app.mongodb)
    chunk_model = await ChunkModel.create_instance(db_client = request.app.mongodb)
    asset_model = await AssetModel.create_instance(db_client = request.app.mongodb)

    process_controller = ProcessController(project_name = str(project_name))

    # setup 
    project = await project_model.get_project_or_insert_it(project_name)
    if process_request.do_reset:
        await chunk_model.delete_chunks_by_project_id(project_id = project.id)

    # get assets to chunk
    if process_request.file_name:
        asset_record = await asset_model.get_asset_record(project_id = project.id, asset_name = process_request.file_name)
        if not asset_record:
            return return_bad_request(message = ResponsesEnum.FILE_INVALID_FILE_NAME.value)
            
        project_files_ids = {asset_record.id : asset_record.asset_name}

    else:
        project_assets = await asset_model.get_all_project_assets(project_id = project.id, asset_type = AssetTypesEnum.ASSET_FILE.value)
        project_files_ids = {record.id : record.asset_name for record in project_assets}
    
    if len(project_files_ids) == 0:
        return return_bad_request(message = ResponsesEnum.PROJECT_FILES_NOT_FOUND.value)


    # chunking file
    no_records_inserted = 0
    no_processed_files = 0
    for asset_id, asset_name in project_files_ids.items():
        file_content = process_controller.get_file_content(file_id = asset_name)

        if file_content is None:
            logger.error(f"Error while loading file: {asset_name}")
            continue

        chunks = process_controller.get_chunks(
            file_content = file_content,
            chunk_size = process_request.chunk_size,
            overlap_size = process_request.overlap_size,
        )
        
        if not chunks or len(chunks) == 0:
            logger.error(f"Error while chunking file: {asset_name}")
    
        # store chunks in db
        chunk_objects = [
            DataChunk(
                chunk_text = chunk.page_content,
                chunk_project_id = project.id,
                chunk_metadata = chunk.metadata,
                chunk_asset_id = asset_id,
                chunk_order = i + 1,
            )
            for i, chunk in enumerate(chunks)
        ]

        no_records_inserted += await chunk_model.insert_many_chunks(chunk_objects)
        no_processed_files += 1


    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            'message': ResponsesEnum.FILE_PROCESSING_SUCCEEDED.value,
            "no_chunks_inserted": no_records_inserted,
            "no_processed_files": no_processed_files
        }
    )