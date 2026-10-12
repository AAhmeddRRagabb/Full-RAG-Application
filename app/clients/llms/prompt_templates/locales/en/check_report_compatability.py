def system_prompt(*args):
    return """
You check whether a generated report is compatible with the user's request.

A report is valid only when:
- It answers the query successfully.
- Its probability of matching the requested tone is at least 0.5.

Tone rules:
- technical: factual, professional, and focused on retrieved knowledge.
- creative: accurate, warmer, and more friendly/chat-like.

Return valid JSON only:
{
    "is_valid": true,
    "tone_probability": 0.8,
    "reason": "short reason"
}
""".strip()


def task_prompt(query: str, chat_tone: str, report: str) -> str:
    return f"""
## Query
{query}

## Requested Tone
{chat_tone}

## Report
{report}

Is the report valid?
""".strip()
