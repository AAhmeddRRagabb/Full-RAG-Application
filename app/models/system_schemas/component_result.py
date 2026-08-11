from pydantic import BaseModel
from typing import Any

class ComponentResult(BaseModel):
    success: bool
    content: Any | None = None
    error  : Any | None = None
    message: str | None = None