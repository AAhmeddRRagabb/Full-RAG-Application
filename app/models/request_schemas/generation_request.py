from pydantic import BaseModel


class GenerationRequest(BaseModel):
    query: str
    limit: int = 5