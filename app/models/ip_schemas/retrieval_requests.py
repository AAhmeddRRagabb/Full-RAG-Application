from pydantic import BaseModel
from typing import Optional


class PushChunksRequest(BaseModel):
    do_reset: Optional[int] = 0

class RetrievalRequest(BaseModel):
    query: str
    limit: int = 5