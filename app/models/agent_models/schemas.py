
from pydantic import BaseModel
from typing import Any


# -- Retrieved Chunk
class RetrievedChunk(BaseModel):
    text: str
    score: float
    chunk_id: int | None = None
    resource: Any | None = None
    publish_date: Any | None = None
