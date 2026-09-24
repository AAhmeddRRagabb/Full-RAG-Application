from string import Template
from models.system_schemas import RetrievedChunk

def system_prompt(*args):
    return """
You are a helpful assistant.
You will be given a list of user requirements & another assitant's response to those requirements.
Your main role is to ensure that all user requirements have been answered & considered.

## Response Format:
Return your findings in the following JSON format:
{
    "all_answered": a boolean indicates whether all user requirements answered or not.
}
""".strip()


# documents summarization
def task_prompt(user_requirements: list[str], assistant_response: str) -> int:
    user_requirements_str = ""
    
    for req in user_requirements:
        user_requirements_str += f"- {req}\n"
    
        return f"""
    ## User Requirements:\n{user_requirements_str}
    ## Assistant Response:\n{assistant_response} 
    """.strip()


    


