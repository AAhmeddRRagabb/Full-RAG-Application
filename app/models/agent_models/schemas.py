
from pydantic import BaseModel, Field
from typing import Any, Literal


# -- Retrieved Chunk
class RetrievedChunk(BaseModel):
    text: str
    score: float

# -- Evidence
class Evidence(BaseModel):
    content: str = Field(..., description = "Information related to the user query.")
    relevance_score: float = Field(..., ge = 0, le = 1, description = "Relevance score between the evidence and the user query.")
    resource: str = Field(..., description = "File name or website URL where the evidence came from.")

class EvidenceResult(BaseModel):
    evidence: list[Evidence] = Field(default_factory = list)
    need_additional_info: bool = False


# -- Report
class AnswerCheckResult(BaseModel):
    answer_found: bool = False
    reason: str = ""
    suggested_query: str | None = None


class FinalReportResult(BaseModel):
    report: str
    resources: list[str] = Field(default_factory = list)


class ReportCompatibilityResult(BaseModel):
    is_valid: bool = False
    tone_probability: float = Field(..., ge = 0, le = 1)
    reason: str = ""

# -- Orchestrator
class AgentState(BaseModel):
    current_date: str | None = None
    current_year: int | None = None
    has_current_date: bool = False

    calculator_result: str | None = None
    has_calculator_result: bool = False

    chat_context: list[str] | None = None
    references: list[dict] | None = None
    has_chat_context: bool = False
    has_references: bool = False

    search_results : list[Evidence] = Field(default_factory = list)
    has_search_results: bool = False
    max_search_limit: int
    search_attempts: int = 0

    answer_found: bool | None = None
    answer_reason: str | None = None

    final_report : str | None = None
    llm_resources: list[str] = Field(default_factory = list)
    has_final_report: bool = False
    has_llm_resources: bool = False
    report_query: str | None = None
    report_compatible: bool | None = None
    report_tone_probability: float | None = None
    report_check_reason: str | None = None
 

class NextAction(BaseModel):
    reason: str
    action: Literal[
        'get_chat_context',
        'get_current_date',
        'calculator',
        'search',
        'check_answer',
        'generate_final_report',
        'check_report_compatability',
        'finish'
    ]
    arguments: dict[str, Any] = Field(default_factory = dict)