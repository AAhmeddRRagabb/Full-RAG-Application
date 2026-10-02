

import os
from .base_controller import BaseController

class UserController(BaseController):
    def __init__(self):
        super().__init__()

    def get_user_path(self, user_key: str) -> str:
        user_key = str(user_key).lower()

        if " " in user_key:
            user_key = '_'.join(user_key.split())

        user_path = os.path.join(self.assests_files_path, f'user_{user_key}')
        os.makedirs(user_path, exist_ok = True)

        return user_path


    def validate_user_name(self, user_name: str) -> bool:
        if "_" in user_name:
            user_name = user_name.replace('_', '')

        return user_name.isalnum()
