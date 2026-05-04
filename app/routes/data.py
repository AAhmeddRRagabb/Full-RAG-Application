from fastapi import APIRouter, Depends, UploadFile, File, status
from fastapi.responses import JSONResponse
import aiofiles
from models import ResponseSignal
import helpers.config as CFG
from controllers import DataController, ProjectController
import os

import logging
logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix = CFG.DATA_ROUTES_PREFIX,
    tags = ["data"]
) 


@data_router.post("/upload/{project_id}")
async def upload_file(
    project_id: str,
    file: UploadFile = File(...),
):
    """
    Uploading a file to the system & saves it. This route mainly do the following:
        - validate the uploaded file
        - clean & standardize its name
        - save it within the system environment
    """
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
                "message" : "File Uploaded Successfully"
            }
        )