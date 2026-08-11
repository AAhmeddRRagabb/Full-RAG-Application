# ----------------------------------------------
# Base Controller Module
# ----------------------------------------------

import os
from typing import Any
from models.system_schemas import ComponentResult

class BaseController:

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))

        # assets dir
        self.assests_files_path = os.path.join(self.base_dir, "assets/files")
        os.makedirs(self.assests_files_path, exist_ok = True) 

        # databases dir
        self.vector_database_dir = os.path.join(self.base_dir, "assets/vector_databases")
        os.makedirs(self.vector_database_dir, exist_ok = True)

    
    def get_vector_database_path(self, vector_db_name: str) -> str:
        vector_db_path = os.path.join(
            self.vector_database_dir,
            vector_db_name
        )

        os.makedirs(vector_db_path, exist_ok = True)
        return vector_db_path



    def _return_success(self, content: Any | None = None, message: str | None = None) -> ComponentResult:
        return ComponentResult(
            success = True,
            content = content,
            message = message
        )

    def _return_failure(self, error: Any | None = None, message: str | None = None) -> ComponentResult:
        return ComponentResult(
            success = False,
            error = error,
            message = message
        )