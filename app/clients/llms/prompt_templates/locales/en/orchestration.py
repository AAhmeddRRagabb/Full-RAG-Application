from models.agent_models.tools import AGENTIC_TOOLS_SERIALIZABLE, WorkflowStep, ToolCall
import json


def system_prompt(*args):
    return f"""
You are an orchestration agent in a professional Chatbot system.
You are given a user_query and your role is to plan to produce the best possible response.

You can use the following tools:
{json.dumps(AGENTIC_TOOLS_SERIALIZABLE, indent=2)}
You should plan your workflow & choose the best appropriate next_action according to the query & your logic..


## Rules:
- max search_limit is 3.
- If the query is direct and does not require search, use `generate_answer` directly.
- After `generate_answer`, use `finish`.


## Example:
- User Query: Tell me current advances in AI.
- Workflow:
    - Orchestrator: I need current info, so I will use `get_current_date`.
    - Action Taken: get_current_date
        Reason: I need current info.
        Result: Current Date is 16-10-2026
    - Orchestrator: I got current date. Now I want info about AI regarding this date, I will search using this search_query 'AI news in 2026'
    - Action Taken: search
        Reason: Now I want info about AI in 2026.
        Result: Search tool returned 0 information pieces.
    - Orchestrator: No relevant information returned. I will retry search using clearer search_query 'Recent advances in AI in 2026'
    - Action Taken: search
        Reason: Search again with clearer search_query.
        Result: Search tool returned 4 information pieces.
    - Orchestrator: I got `search_results`. I will generate the answer.
    - Action Taken: generate_answer:
        Reason: found relevant search results, so it is time for generation.
        Result: True
    - Orchestrator: Answer is generated. I will finish.
    - Action Taken: finish:
        Reason: Answer is ready.
        Result: None


Use your logic & the given tools to determine the next_action.
Return valid JSON only:
{{
    "reason": "brief reason of why you have choose that action",
    "action": "get_current_date | calculate | search | generate_answer | finish",
    "arguments": {{}}
}}
""".strip()



# documents summarization
def format_tool_call(tool_call: ToolCall) -> str:
    formatted = f"""
- Action Taken: {tool_call.tool_name}
\t Reason: {tool_call.tool_reason}
\t Result: {tool_call.tool_result}
""".strip()

    return formatted



def task_prompt(workflow: list[WorkflowStep]) -> str:
    prompt = ""

    for step in workflow:
        if step.step_name == "user_query":
            prompt += f"## User Query: {step.user_query}\n\n"

        elif step.step_name == "tool_call":
            prompt += format_tool_call(step.step_details)
            prompt += "\n"

    return prompt.strip()



    


