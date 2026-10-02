from pydantic import BaseModel, Field
from typing import Any, Literal


class Evidence(BaseModel):
    content: str = Field(..., description = "Information related to the user query.")
    relevance_score: float = Field(..., ge = 0, le = 1, description = "Relevance score between the evidence and the user query.")
    resource: str = Field(..., description = "File name or website URL where the evidence came from.")


class QueryUnderstandingResult(BaseModel):
    requirements: list[str] = Field(default_factory = list)


class EvidenceResult(BaseModel):
    evidence: list[Evidence] = Field(default_factory = list)
    need_additional_info: bool = False




class AnswerCheckResult(BaseModel):
    answer_found: bool = False
    reason: str = ""
    suggested_query: str | None = None


class FinalReportResult(BaseModel):
    report: str
    resources: list[str] = Field(default_factory = list)


class AgentState(BaseModel):
    chat_context: list[str] | None = None
    references: list[dict] | None = None

    search_results : list[Evidence] = Field(default_factory = list)

    final_report : str | None = None
    llm_resources: list[str] = Field(default_factory = list)

    max_search_limit: int
    search_attempts: int = 0

    total_completed_agentic_steps: int = 0    


class NextAction(BaseModel):
    reason: str
    action: Literal[
        'get_chat_context',
        'search',
        'generate_final_report',
        'finish'
    ]
    arguments: dict[str, Any] = Field(default_factory = dict)
