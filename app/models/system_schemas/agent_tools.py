from typing import Any

from pydantic import BaseModel


class ToolDefinition(BaseModel):
    name       : str
    description: str
    parameters : dict[str, Any]
    returns    : dict[str, Any]


AGENTIC_TOOLS = {
    "get_chat_context": ToolDefinition(
        name = "get_chat_context",
        description = "Access previous chat messages to further understand the user query within the chat context.",
        parameters = {},
        returns = {
            "chat_context": {"type": "object | null"},
        },
    ),

    "get_current_date": ToolDefinition(
        name = "get_current_date",
        description = "Get the current date and year from the server clock. Use this for current/latest/recent/time-sensitive questions.",
        parameters = {},
        returns = {
            "current_date": {"type": "string"},
            "current_year": {"type": "integer"},
        },
    ),

    "calculator": ToolDefinition(
        name = "calculator",
        description = "Evaluate a deterministic arithmetic expression.",
        parameters = {
            "expression": {
                "type": "string",
                "description": "Arithmetic expression to evaluate.",
            },
        },
        returns = {
            "result": {"type": "string"},
        },
    ),

    "search": ToolDefinition(
        name = "search",
        description = "Search selected files and the web using the orchestrator-provided research query.",
        parameters = {
            "query": {
                "type": "string",
                "description": "Query used for both file search and web search.",
            },
        },
        returns = {
            "search_results": {"type": "list"},
        },
    ),

    "check_answer": ToolDefinition(
        name = "check_answer",
        description = "Check whether current search evidence contains enough information to answer.",
        parameters = {},
        returns = {
            "answer_found": {"type": "bool"},
            "reason": {"type": "string"},
        },
    ),

    "generate_final_report": ToolDefinition(
        name = "generate_final_report",
        description = "Generate the final answer. It may answer directly when search evidence is not needed.",
        parameters = {
            "query": {
                "type": "string",
                "description": "Best final query to answer after context/search refinement.",
            },
        },
        returns = {
            "report": {"type": "string"},
            "resources": {"type": "list"},
        },
    ),

    "check_report_compatability": ToolDefinition(
        name = "check_report_compatability",
        description = "Check whether the generated report answers the selected query and matches the requested tone.",
        parameters = {},
        returns = {
            "is_valid": {"type": "bool"},
            "tone_probability": {"type": "float"},
            "reason": {"type": "string"},
        },
    ),

    "finish": ToolDefinition(
        name = "finish",
        description = "Finish the workflow. This is deterministic and only breaks the loop.",
        parameters = {},
        returns = {},
    ),
}


AGENTIC_TOOLS_SERIALIZABLE = {
    name: tool.model_dump()
    for name, tool in AGENTIC_TOOLS.items()
}
