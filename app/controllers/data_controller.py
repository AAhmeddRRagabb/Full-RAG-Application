import re
import aiofiles

from models.enums import ResponsesEnum
from helpers.config import FILE_ALLOWED_TYPES, FILE_MAX_SIZE_MB, FILE_CHUNK_SIZE_B

from .base_controller import BaseController
from fastapi import UploadFile

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.mb_2_b = 1024 * 1024


    def validate_uploaded_file(self, file: UploadFile) -> dict[str, bool | str]:
        """
        Validate the uploaded file size & type

        Returns:
            dict contains:
                if valid ->
                    - valid = True
                    - message = valid message
                if not valid ->
                    - valid = False
                    - message = not valid message
        """
        
        if file.content_type not in FILE_ALLOWED_TYPES:
            return {
                "valid": False,
                "message": ResponsesEnum.FILE_TYPE_NOT_SUPPORTED.value
            }
        
        if file.size > FILE_MAX_SIZE_MB * self.mb_2_b:
            return {
                "valid": False,
                "message": ResponsesEnum.FILE_MAX_SIZE_EXCEEDED.value
            }

        return {
            "valid": True,
            "message": ResponsesEnum.FILE_UPLOADING_SUCCESS.value
        }

    
    def clean_file_name(self, file_name: str) -> str | None:
        """Clean & Standardize the file name"""
        try:
            cleaned_fname = re.sub(r'[^\w.]', '', file_name.strip()) # \w --> [A-Z a-z 0-9 _]
            cleaned_fname = cleaned_fname.replace(' ', '_')
        except Exception as e:
            self.logger.error(f"Error Cleaning Filename: {e}")
            return None
        
        return cleaned_fname


    async def save_file(self, file: UploadFile, file_path: str) -> bool:
        """
        Returns:
            a bool indicates whether the file has been saved successfully or not.
        """
        try:
            async with aiofiles.open(file = file_path, mode = 'wb') as f:
                while chunk := await file.read(size = FILE_CHUNK_SIZE_B):
                    await f.write(chunk)
        except Exception as e:
            self.logger.error(f"Error Saving File: {e}")
            return False

        return True