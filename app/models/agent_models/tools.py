from typing import Any
from pydantic import BaseModel
from typing import Literal


class ToolDefinition(BaseModel):
    name       : str
    description: str
    parameters : dict[str, Any]
    returns    : dict[str, Any]


AGENTIC_TOOLS = {
    "get_current_date": ToolDefinition(
        name = "get_current_date",
        description = "Get the current date and year from the server clock. Use this for current/latest/recent/time-sensitive questions.",
        parameters = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        },
        returns = {
            "date_response": {"type": "string"},
        }
    ),

    "calculate": ToolDefinition(
        name = "calculate",
        description = "Evaluate a deterministic arithmetic expression.",
        parameters = {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Arithmetic expression to evaluate."
                },
                "natural_language_expression": {
                    "type": "string",
                    "description": "The same expression but in natural language. For logging cases."
                }
            },
            "required": ["expression", "natural_language_expression"],
            "additionalProperties": False
        },
        returns = {
            "result": {
                "type": "string",
                "description": "Result of the expression."
            },
        }
    ),

    "search": ToolDefinition(
        name = "search",
        description = "Search selected files and the web using the orchestrator-provided search_query.",
        parameters = {
            "type": "string",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "Query used for both file search and web search."
                }
            },
            "required": ["search_query"],
            "additionalProperties": False
        },
        returns = {
            "search_results": {
                "type": "string",
                "description": "the results returned from the search."
            }
        }
    ),

    "generate_answer": ToolDefinition(
        name = "generate_answer",
        description = "Generate the final answer. It may answer directly when search is not needed.",
        parameters = {
            "type": "object",
            "properties": {
                "generation_query": {
                    "type": "string",
                    "description": "Best final query help to answer after search / date refinement.",
                }
            },
            "required": ["generation_query"],
            "additionalProperties": False
        },
        returns = {
            "report": {
                "type": "string",
                "description": "answer generated"
            },
            "resources": {
                "type": "list",
                "description": "resources for the answer"
            },
        }
    ),

    "finish": ToolDefinition(
        name = "finish",
        description = "Finish the workflow. This is deterministic and only breaks the loop.",
        parameters = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False
        },
        returns = {},
    ),
}


AGENTIC_TOOLS_SERIALIZABLE = {
    name: tool.model_dump()
    for name, tool in AGENTIC_TOOLS.items()
}



# -- Tool Calls
class ToolCall(BaseModel):
    tool_name: Literal[
        'get_current_date',
        'calculate',
        'search',
        'generate_answer',
        'finish'
    ]
    tool_reason: str
    tool_input: str | None = None
    tool_result: str



class WorkflowStep(BaseModel):
    step_name: Literal["user_query", "tool_call"]
    user_query: str | None = None
    step_details: ToolCall | None = None
