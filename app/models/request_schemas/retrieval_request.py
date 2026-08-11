from pydantic import BaseModel
from typing import Optional



class RetrievalRequest(BaseModel):
    query: str
    limit: int = 5