def system_prompt(*args):
    return """
You validate whether a generated answer responds to the user's query.
Return valid JSON only:
{"valid": true}
Use false when the answer does not respond to the query.
""".strip()


def task_prompt(user_query: str, answer: str) -> str:
    return f"User Query: {user_query}\nAnswer: {answer}"
