def system_prompt():
    return (
        "Compare the two PDFs according to the user's question using only the supplied excerpts. "
        "Describe relevant similarities and differences clearly. If one or both files lack enough "
        "information, say so. Do not invent details. Reply in the user's language in concise Markdown."
    )


def task_prompt(query: str, files: list[dict]):
    sections = []
    for file in files:
        excerpts = "\n\n".join(file["excerpts"]) or "No relevant excerpts found."
        sections.append(f"File: {file['name']}\n{excerpts}")
    return f"Comparison question: {query}\n\n" + "\n\n".join(sections)
