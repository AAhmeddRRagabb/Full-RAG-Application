import re
import aiofiles

from models.system_schemas import ComponentResult
from models.enums import ResponsesEnum
from helpers.config import FILE_ALLOWED_TYPES, FILE_MAX_SIZE_MB, FILE_CHUNK_SIZE_B

from .base_controller import BaseController
from fastapi import UploadFile

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.mb_2_b = 1024 * 1024


    def validate_uploaded_file(self, file: UploadFile) -> ComponentResult:
        """
        Validate the uploaded file size & type

        Returns:
            ComponentResult:
                if valid ->
                    - success = True
                    - message = valid message
                if not valid ->
                    - success = False
                    - message = not valid message
        """
        
        if file.content_type not in FILE_ALLOWED_TYPES:
            return self._return_failure(message = ResponsesEnum.FILE_TYPE_NOT_SUPPORTED.value)
        
        if file.size > FILE_MAX_SIZE_MB * self.mb_2_b:
            return self._return_failure(message = ResponsesEnum.FILE_MAX_SIZE_EXCEEDED.value)

        return self._return_success(message = ResponsesEnum.FILE_UPLOADING_SUCCESS.value)

    
    def clean_file_name(self, file_name: str):
        """Clean & Standardize the file name"""
        cleaned_fname = re.sub(r'[^\w.]', '', file_name.strip()) # \w --> [A-Z a-z 0-9 _]
        cleaned_fname = cleaned_fname.replace(' ', '_')
        return self._return_success(content = cleaned_fname)

    async def save_file(self, file, file_path: str) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: None
                if error   -> error & error type
        """
        try:
            async with aiofiles.open(file = file_path, mode = 'wb') as f:
                while chunk := await file.read(size = FILE_CHUNK_SIZE_B):
                    await f.write(chunk)
        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.FILE_UPLOADING_INNER_ERROR.value)

        return self._return_success()