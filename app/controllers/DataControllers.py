
from .BaseController import BaseController
from fastapi import UploadFile
from helpers.config import FILE_ALLOWED_TYPES 
from models import ResponseSignal
import re

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.mb_2_b = 1024 * 1024

    def validate_uploaded_file(self, file: UploadFile):
        if file.content_type not in FILE_ALLOWED_TYPES:
            return {
                "status" : "error",
                "message": ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value
            }
        
        if file.size > self.app_settings.FILE_MAX_SIZE_MB * self.mb_2_b:
            return {
                "status" : "error",
                "message": ResponseSignal.FILE_MAX_SIZE_EXCEEDED.value
            }
        
        return {
            "status" : "success",
            "message": ResponseSignal.FILE_UPLOADED_SUCCESSFULLY.value
        }
    
    def clean_file_name(self, file_name: str):
        cleaned_fname = re.sub(r'[^\w.]', '', file_name.strip()) # \w --> [A-Z a-z 0-9 _]
        cleaned_fname = cleaned_fname.replace(' ', '_')
        return cleaned_fname