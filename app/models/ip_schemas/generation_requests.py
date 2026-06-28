from pydantic import BaseModel
from typing import Optional




class AnswerUserQueryRequest(BaseModel):
    query: str
    limit: int = 5