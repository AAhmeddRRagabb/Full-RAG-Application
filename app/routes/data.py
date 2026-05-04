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
    app_settings: CFG.Settings = Depends(dependency = CFG.get_settings),
):
    # validate file
    print(" Data Uploading ".center(100, "="))
    data_controller = DataController()
    
    result = data_controller.validate_uploaded_file(file = file)
    if result['status'] == "error":
        return JSONResponse(
            status_code = status.HTTP_400_BAD_REQUEST,
            content = {
                "message" : result['message']
            }
        )

    # saving the given file
    cleaned_filename = data_controller.clean_file_name(file_name = file.filename)
    project_path = ProjectController().get_project_path(project_id = project_id)
    file_path = os.path.join(project_path, cleaned_filename)

    # save the file in chunks
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


    return JSONResponse(
            status_code = status.HTTP_200_OK,
            content = {
                "message" : "File Uploaded Successfully"
            }
        )