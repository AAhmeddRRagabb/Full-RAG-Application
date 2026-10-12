def system_prompt(*args):
    return """
You resolve references in a user's query using prior chat messages.
Messages are provided in chronological order, from oldest to newest.

Resolve references such as pronouns, names, and phrases like
"him", "that", "the previous one", or "it".

Extract only the information needed to understand references or vague wording.
Do not answer the query. Do not include facts that are not needed to resolve references.

Return valid JSON only:
{
    "chat_context": ["reference-resolution context item"],
    "references": [
        {
            "reference": "him",
            "resolved_to": "Someone"
        },
        {
            "reference": "it",
            "resolved_to": "Something / place / animal / ..."
        }
    ]
}

where:
- chat_context: Up to three short items that resolve references or vague wording only.
- references: list of (reference - resolved to) pairs.

""".strip()


def task_prompt(user_query: str, messages: list[str]) -> str:
    messages_str = "\n"
    for message in messages:
        messages_str += f'- {message}\n'

    return f"""
## User Query: {user_query}

## Messages: {messages_str}
## Your Response:
    """.strip()
