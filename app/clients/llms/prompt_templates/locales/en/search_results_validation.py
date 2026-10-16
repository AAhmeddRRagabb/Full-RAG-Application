import json


def system_prompt(*args):
    return f"""
You are a helpful assistant in an agentic AI system.
You will be given:
- user_query (str)
- list of search_results retrieved from searching.

Your only role is to determine if the `user_query` can be answered by the `search_results` or not.

Return valid JSON only:
{{
    "valid": "bool determines if the `user_query` can be answered using the `search_results` or not",
}}
""".strip()





def task_prompt(user_query: str, search_results: list[dict]) -> str:
    return f"User Query: {user_query}\nSearch Results: {json.dumps(search_results, ensure_ascii=False)}"



    


