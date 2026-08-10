# ------------------------------------------------------
# Implementing the routes related to the data
# -------------------------------------------------------

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
from models.ip_schemas import ProcessRequest


# controllers
from controllers import ProjectController
from controllers import DataController
from controllers import ProcessController
from controllers import NLPController

# helpers
import helpers.config as CFG
import os


import logging
logger = logging.getLogger("uvicorn.error")

data_pipeline_router = APIRouter(
    prefix = CFG.DATA_ROUTES_PREFIX,
    tags = ["data"]
) 


# --- helpers
def return_bad_request(message: str) -> JSONResponse:
    return JSONResponse(
        status_code = status.HTTP_400_BAD_REQUEST,
        content = {
            "success": False,
            "message": message
        }
    )


# --- endpoints 

@data_pipeline_router.post("/upload/{project_name}")
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
    # setup
    data_controller = DataController()

    project_model = ProjectModel(db_client = request.app.db_client)
    asset_model   = AssetModel(db_client = request.app.db_client)

    project_path    = ProjectController().get_project_path(project_name = project_name)

    # processing file
    validation_results = data_controller.validate_uploaded_file(file = file)
    if not validation_results.success:
        return return_bad_request(message = validation_results.message)
  
    cleaned_filename = data_controller.clean_file_name(file_name = file.filename).content
    file_path = os.path.join(project_path, cleaned_filename)

    saved_file_result = await data_controller.save_file(file = file, file_path = file_path)
    if not saved_file_result.success:
        logger.error(f"Error while saving the file: {saved_file_result.error}")
        return return_bad_request(message = saved_file_result.message)

    
    # save project
    insert_project_result = await project_model.get_project_or_insert_it(project_name = project_name)
    if not insert_project_result.success:
        if insert_project_result.error:
            logger.error(f"Error while accessing the project: {insert_project_result.error}")

        return return_bad_request(message = insert_project_result.message)


    # save asset
    project = insert_project_result.content
    asset = Asset(
        asset_project_id = project.project_id,
        asset_type = AssetTypesEnum.ASSET_FILE.value,
        asset_name = cleaned_filename,
        asset_size = os.path.getsize(file_path)
    )

    asset_record_result = await asset_model.create_asset(asset)
    if not asset_record_result.success:
        logger.error(f"Error while saving the asset: {asset_record_result.error}")
        return return_bad_request(message = asset_record_result.message)


    # return on success
    asset_record = asset_record_result.content
    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            "success": True,
            "message": ResponsesEnum.FILE_UPLOADING_SUCCESS.value,
            "file_uploaded_name": asset_record.asset_name
        }
    )



@data_pipeline_router.post("/process/{project_name}")
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
    # setup
    project_model = ProjectModel(db_client = request.app.db_client)
    chunk_model   = ChunkModel(db_client = request.app.db_client)
    asset_model   = AssetModel(db_client = request.app.db_client)

    process_controller = ProcessController(project_name = str(project_name))

    nlp_controller = NLPController(
        vector_db_client = request.app.vector_db_client,
        embedding_client = request.app.embedding_client,
    )


    project_result = await project_model.get_project_or_insert_it(project_name)
    if not project_result.success:
        if project_result.error:
            logger.error(f"Error while accessing the project: {project_result.error}")
        return return_bad_request(message = project_result.message)
    
    project = project_result.content

    # resetting
    if process_request.do_reset:
        # delete chunks
        chunks_delete_result = await chunk_model.delete_chunks_by_project_id(project_id = project.project_id)
        if not chunks_delete_result.success:
            logger.error(f"Error while deleting chunks: {chunks_delete_result.error}")
            return return_bad_request(message = project_result.message)


        # delete vectors
        collection_name = nlp_controller.get_collection_name(project_name)
        vectors_delete_result = await nlp_controller.delete_collection(collection_name)
        if not vectors_delete_result.success:
            logger.error(f"Error while deleting vectors: {vectors_delete_result.error}")
            return return_bad_request(message = vectors_delete_result.message)



    # get assets to chunk
    if process_request.file_name:
        asset_record_result = await asset_model.get_asset_record(project_id = project.project_id, asset_name = process_request.file_name)
        if not asset_record_result.success:
            logger.error(f"Error while accessing asset: {asset_record_result.error}")
            return return_bad_request(message = asset_record_result.message)

        asset_record = asset_record_result.content
        if not asset_record:
            return return_bad_request(message = ResponsesEnum.ASSET_INNER_ERROR.value)
        
        project_files_ids = {asset_record.asset_id : asset_record.asset_name}

    else:
        project_assets_result = await asset_model.get_all_project_assets(project_id = project.project_id, asset_type = AssetTypesEnum.ASSET_FILE.value)
        if not project_assets_result.success:
            logger.error(f"Error while accessing assets: {project_assets_result.error}")
            return return_bad_request(message = project_assets_result.message)

        project_files_ids = {record.asset_id : record.asset_name for record in project_assets_result.content}

    if len(project_files_ids) == 0:
        return return_bad_request(message = ResponsesEnum.ASSET_INNER_ERROR.value)


    # chunking file
    no_records_inserted = 0
    no_processed_files = 0
    for asset_id, asset_name in project_files_ids.items():
        file_content = process_controller.get_file_content(file_id = asset_name)

        if file_content is None:
            logger.error(f"Error while loading file: {asset_name}. File Content: {file_content}")
            continue

        chunking_result = process_controller.get_chunks(
            file_content = file_content,
            chunk_size = process_request.chunk_size,
            overlap_size = process_request.overlap_size,
        )

        if not chunking_result.success:
            logger.error(f"Error while chunking file: {asset_name}.")
            continue

        chunks = chunking_result.content
        if not chunks or len(chunks) == 0:
            logger.error(f"Error while chunking file: {asset_name}. Chunks: {chunks}")
            continue
    
        # store chunks in db
        chunk_objects = [
            DataChunk(
                chunk_text = chunk.page_content,
                chunk_project_id = project.project_id,
                chunk_metadata = chunk.metadata,
                chunk_asset_id = asset_id,
                chunk_order = i + 1,
            )
            for i, chunk in enumerate(chunks)
        ]

        insertion_result = await chunk_model.insert_many_chunks(chunk_objects)
        if not insertion_result.success:
            logger.error(f"Error while saving chunk: {insertion_result.error}")
            continue

        
        no_records_inserted += insertion_result.content
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
