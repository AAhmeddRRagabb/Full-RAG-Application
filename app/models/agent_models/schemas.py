
from pydantic import BaseModel, Field
from typing import Any, Literal


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

class EvidenceResult(BaseModel):
    evidence: list[Evidence] = Field(default_factory = list)
    need_additional_info: bool = False


class FinalAnswer(BaseModel):
    answer: str
    resources: list[str] = Field(default_factory = list)


# -- Orchestrator
class NextAction(BaseModel):
    reason: str
    action: Literal[
        'get_current_date',
        'calculate',
        'search',
        'generate_answer',
        'finish'
    ]
    arguments: dict[str, Any] = Field(default_factory = dict)
