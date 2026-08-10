# -------------------------------------------------------
# Building a Base Model to store/load/act on database 
# -------------------------------------------------------
from typing import Any
from helpers.config import get_settings
from pydantic import BaseModel

class ObjectModelResult(BaseModel):
    success: bool
    content: Any | None = None
    message: str | None = None
    error  : Any | None = None

class BaseObjModel:
    def __init__(self, db_client: object):
        self.db_client = db_client
        self.settings = get_settings()

    def _return_success(self, content: Any | None = None) -> ObjectModelResult:
        return ObjectModelResult(
            success = True,
            content = content
        )

    def _return_failure(self, message: str | None = None, error: Any | None = None) -> ObjectModelResult:
        return ObjectModelResult(
            success = False,
            message = message,
            error = error
        )
        