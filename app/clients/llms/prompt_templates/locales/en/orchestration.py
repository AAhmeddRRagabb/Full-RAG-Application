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
- max answer_generation_limit is 3.
- If the query is direct and does not require search, use `generate_answer` directly.


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
        Result: `search_results`
    - Orchestrator: I got `search_results`. I should validate it.
    - Action Taken: validate_search_results:
        Reason: need to validate search_results.
        Result: False
    - Orchestrator: Search results is not valid. Since I have searched once and search_limit is 3, I will search again with a clearer search_query 'Top AI news in 2026'.
    - Action Taken: search
        Reason: Now I want info about AI in 2026.
        Result: `search_results`
    - Orchestrator: I got `search_results`. I should validate it.
    - Action Taken: validate_search_results:
        Reason: need to validate search_results.
        Result: True
    - Orchestrator: Search results is valid. I will generate the answer.
    - Action Taken: generate_answer:
        Reason: found relevant search results, so it is time for generation.
        Result: answer_generated
    - Orchestrator: Answer is generated. I will validate it.
    - Action Taken: validate_answer:
        Reason: need to validate answer.
        Result: True
    - Orchestrator: Answer is valid. I will finish.
    - Action Taken: finish:
        Reason: Answer is valid.
        Result: None


Use your logic & the given tools to determine the next_action.
Return valid JSON only:
{{
    "reason": "brief reason of why you have choose that action",
    "action": "get_current_date | calculate | search | validate_search_results | generate_answer | validate_answer | finish",
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



    


