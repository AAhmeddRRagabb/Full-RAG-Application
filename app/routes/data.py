from fastapi import APIRouter, Depends, UploadFile, File, status, Request
from fastapi.responses import JSONResponse
import aiofiles
from models import ResponseSignal
import helpers.config as CFG
from controllers import DataController, ProjectController, ProcessController
import os
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.db_schemas import DataChunk

import logging
logger = logging.getLogger("uvicorn.error")


from .schemes.data import ProcessRequest

data_router = APIRouter(
    prefix = CFG.DATA_ROUTES_PREFIX,
    tags = ["data"]
) 


@data_router.post("/upload/{project_id}")
async def upload_file(
    request: Request,
    project_id: str,
    file: UploadFile = File(...),
):
    """
    Uploading a file to the system & saves it. This route mainly do the following:
        - validate the uploaded file
        - clean & standardize its name
        - save it within the system environment
    """

    
    project_model = await ProjectModel.create_instance(db_client = request.app.mongodb)
    project = await project_model.get_project_or_insert_it(project_id = project_id)

    # validate file
    print(" Data Uploading ".center(100, "="))
    data_controller = DataController()
    
    validation_results = data_controller.validate_uploaded_file(file = file)
    if validation_results['status'] == "error":
        return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content = {
                "message" : validation_results['message']
            }
        )


    # saving the given file [in chunks]
    cleaned_filename = data_controller.clean_file_name(file_name = file.filename)
    project_path = ProjectController().get_project_path(project_id = project_id)
    file_path = os.path.join(project_path, cleaned_filename)


    try:
        async with aiofiles.open(file = file_path, mode = 'wb') as f:
            while chunk := await file.read(size = CFG.FILE_CHUNK_SIZE_B):
                await f.write(chunk)

    except Exception as e:
        print(f"Error while uploading a file: {e}")
        return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content = {
                "message" : ResponseSignal.FILE_UPLOADED_FAILED.value
            }
        )


    # return on success
    return JSONResponse(
            status_code = status.HTTP_200_OK,
            content = {
                "message"  : ResponseSignal.FILE_UPLOADED_SUCCESSFULLY.value,
                "file_name": cleaned_filename,
            }
        )





@data_router.post("/process/{project_id}")
async def process_uploaded_data(
    request: Request,
    project_id: str,
    process_request: ProcessRequest,
):

    # get project
    project_model = await ProjectModel.create_instance(db_client = request.app.mongodb)
    project = await project_model.get_project_or_insert_it(project_id)

    # process the data
    process_controller = ProcessController(project_id = str(project_id))


    # chunking file
    file_content = process_controller.get_file_content(file_id = process_request.file_id)
    chunks = process_controller.get_chunks(
        file_content = file_content,
        chunk_size = process_request.chunk_size,
        overlap_size = process_request.overlap_size,
    )

    if not chunks or len(chunks) == 0:
        return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content = {
                "message": ResponseSignal.FILE_PROCESSING_FAILED.value,
            }
        )
    

    # store in db
    chunk_model = await ChunkModel.create_instance(db_client = request.app.mongodb)
    chunk_objects = [DataChunk(
            chunk_text = chunk.page_content,
            chunk_project_id = str(project._id),
            chunk_metadata = chunk.metadata,
            chunk_order = i + 1 
        )

        for i, chunk in enumerate(chunks)
    ]

    # delete already existing chunks [if required ]
    if process_request.do_reset:
        await chunk_model.delete_chunks_by_project_id(project_id = str(project._id))

    no_records_inserted = await chunk_model.insert_many_chunks(chunk_objects)

    return JSONResponse(
        status_code = status.HTTP_200_OK,
        content = {
            'message': ResponseSignal.FILE_PROCESSING_SUCCEEDED.value,
            "no_chunks_inserted": no_records_inserted
        }
    )