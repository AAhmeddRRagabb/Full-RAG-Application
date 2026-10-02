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

    "search": ToolDefinition(
        name = "search",
        description = "Search selected files and/or the web.",
        parameters = {
            "query": {"type": "string"},
        },
        returns = {
            "search_results": {"type": "list"},
        },
    ),

    "generate_final_report": ToolDefinition(
        name = "generate_final_report",
        description = "Generate the final answer.",
        parameters = {
            "query": {"type": "string"},
            "search_results": {"type": "list"},
            "answer_mode": {"type": "direct | grounded"},
            "final_tone": {"type": "technical | creative"},
        },
        returns = {
            "report": {"type": "string"},
            "resources": {"type": "list"},
        },
    ),

    "finish": ToolDefinition(
        name = "finish",
        description = "Finish when the final report answers the user query.",
        parameters = {
            "report": {"type": "string"},
            "resources": {"type": "list"},
        },
        returns = {
            "report": {"type": "string"},
            "resources": {"type": "list"},
        },
    ),
}


AGENTIC_TOOLS_SERIALIZABLE = {
    name: tool.model_dump()
    for name, tool in AGENTIC_TOOLS.items()
}
