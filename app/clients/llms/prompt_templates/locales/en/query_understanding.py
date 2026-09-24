from string import Template
from models.system_schemas import RetrievedChunk

def system_prompt(*args):
    return """
You are a helpful assistant.
You will be given a user query.
Your main role is to understand the user query well, extract exactly what user requires, and return these requirements.

## Example:
Query: How does human heart work & what is it composed of?

## User Requirements:
[
    'User wants to know how does human heart works',
    'User wants to know what human heart is composed of.
]

## Response Format:
Return your findings in the following JSON format:
{
    "user_requirements": ['str']
}
""".strip()


# documents summarization
def task_prompt(query) -> str:
    return f"""
## Query: {query}
    
## User Requirements: 
    """.strip()
