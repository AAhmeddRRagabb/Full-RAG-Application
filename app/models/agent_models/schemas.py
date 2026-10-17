
from pydantic import BaseModel, Field
from typing import Any


# -- Retrieved Chunk
class RetrievedChunk(BaseModel):
    text: str
    score: float
    resource: Any | None = None
    publish_date: Any | None = None

# -- Evidence
class Evidence(BaseModel):
    content: str = Field(..., description = "Information related to the user query.")
    relevance_score: float = Field(..., ge = 0, le = 1, description = "Relevance score between the evidence and the user query.")
    resource: str = Field(..., description = "File name or website URL where the evidence came from.")

class FinalAnswer(BaseModel):
    answer: str = Field(min_length=1)
    resources: list[str] = Field(default_factory = list)


class QueryAnalysis(BaseModel):
    need_search: bool
    need_current_info: bool
    resolved_query: str = Field(min_length=1)


class SearchQuery(BaseModel):
    query: str = Field(min_length=1)
