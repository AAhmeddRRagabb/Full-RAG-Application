

import os
from .base_controller import BaseController
from models.system_schemas import ComponentResult
from models.enums import ResponsesEnum

class UserController(BaseController):
    def __init__(self):
        super().__init__()

    def get_user_path(self, user_name: str):
        user_name = user_name.lower()

        if " " in user_name:
            user_name = '_'.join(user_name.split())

        user_path = os.path.join(self.assests_files_path, f'user_{user_name}')
        os.makedirs(user_path, exist_ok = True)

        return user_path


    def validate_user_name(self, user_name: str) -> ComponentResult:
        if "_" in user_name:
            user_name = user_name.replace('_', '')

        valid = user_name.isalnum()

        if valid:
            return self._return_success()

        return self._return_failure(message = ResponsesEnum.USER_INVALID_NAME.value)