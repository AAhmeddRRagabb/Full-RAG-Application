# -------------------------------------------------------
# Building a Base Model to store/load/act on database 
# -------------------------------------------------------
from typing import Any
from helpers.config import get_settings
from models.system_schemas import ComponentResult

class BaseObjModel:
    def __init__(self, db_client: object):
        self.db_client = db_client
        self.settings = get_settings()

    def _return_success(self, content: Any | None = None) -> ComponentResult:
        return ComponentResult(
            success = True,
            content = content
        )

    def _return_failure(self, message: str | None = None, error: Any | None = None) -> ComponentResult:
        return ComponentResult(
            success = False,
            message = message,
            error = error
        )
        