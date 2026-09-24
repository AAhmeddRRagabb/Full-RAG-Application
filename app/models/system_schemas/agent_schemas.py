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


class FinalReportResult(BaseModel):
    report: str
    resources: list[str] = Field(default_factory = list)


class AgentState(BaseModel):
    user_query: str
    requirements: list[str] = Field(default_factory = list)
    
    retrieved_chunks: list[Evidence] = Field(default_factory = list)
    web_results     : list[Evidence] = Field(default_factory = list)

    final_report: str | None = None
    llm_resources: list[str] = Field(default_factory = list)
    completed_steps: list[dict[str, Any]] = Field(default_factory = list)






class NextAction(BaseModel):
    reason: str
    action: Literal[
        'understand_user_query',
        'search_files',
        'search_web',
        'generate_final_report',
        'finish'
    ]
    arguments: dict[str, Any] = Field(default_factory = dict)


class ToolDefinition(BaseModel):
    name        : str
    description : str
    parameters  : dict[str, Any]
    returns     : dict[str, Any]




AGENTIC_TOOLs = {
    "understand_user_query": ToolDefinition(
        name = "understand_user_query",
        description = "Decompose user query into manageable requirements.",
        parameters = {
            "query": {
                "type": "string",
                "description": "The original user query to be understood and decomposed."
            }
        },
        returns = {
            "requirements": {
                "type": "list",
                "description": "List of specific requirements needed to answer the user query."
            }
        }
    ),

    "search_files": ToolDefinition(
        name = "search_files",
        description = "Search selected uploaded files for information related to the user query.",
        parameters = {
            "query": {
                "type": "string",
                "description": "The query or requirement to search for in uploaded files."
            },
            "files": {
                "type": "list",
                "description": "Selected file names or file identifiers to search in."
            },
            "retrieve_limit": {
                "type": "integer",
                "description": "Maximum number of relevant chunks from each file to retrieve."
            }
        },
        returns = {
            "retrieved_chunks": {
                "type": "list",
                "description": "Evidence extracted from selected files. Each item contains content, relevance-score, and resource."
            }
        }
    ),

    "search_web": ToolDefinition(
        name = "search_web",
        description = "Search the web for external information related to the user query.",
        parameters = {
            "query": {
                "type": "string",
                "description": "The query or requirement to search for online."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of search results."
            }
        },
        returns = {
            "web_results": {
                "type": "list",
                "description": "Relevant web results with content, relevance-score, and URL."
            }
        }
    ),

    "generate_final_report": ToolDefinition(
        name = "generate_final_report",
        description = "Generate a report from retrieved file chunks and web results.",
        parameters = {
            "query": {
                "type": "string",
                "description": "The original user query."
            },
            "retrieved_chunks": {
                "type": "list",
                "description": "Evidence extracted from uploaded files."
            },
            "web_results": {
                "type": "list",
                "description": "Evidence extracted from web results."
            }
        },
        returns = {
            "report": {
                "type": "string",
                "description": "Generated report grounded in retrieved information."
            },
            "resources": {
                "type": "list",
                "description": "Resources used by the model to generate the report."
            }
        }
    ),

    "finish": ToolDefinition(
        name = "finish",
        description = "Finish when the final report answers the user query.",
        parameters = {
            "report": {
                "type": "string",
                "description": "Final report to return to the user."
            },
            "resources": {
                "type": "list",
                "description": "Resources used to produce the final report."
            }
        },
        returns = {
            "report": {
                "type": "string",
                "description": "Final report."
            },
            "resources": {
                "type": "list",
                "description": "Final list of resources used by the LLM."
            }
        }
    )
}

AGENTIC_TOOLS_SERIALIZABLE = {
    tool_name: tool_definition.model_dump()
    for tool_name, tool_definition in AGENTIC_TOOLs.items()
}
