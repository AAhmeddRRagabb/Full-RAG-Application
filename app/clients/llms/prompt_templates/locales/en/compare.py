def system_prompt():
    return (
        "Compare the two PDFs according to the user's question using only the supplied excerpts. "
        "Describe relevant similarities and differences clearly. If one or both files lack enough "
        "information, say so. When the excerpts are sufficient, compare directly without notes about "
        "the information being sufficient or about needing more details. Do not invent details. "
        "Reply in English only, in concise Markdown."
    )


def task_prompt(query: str, files: list[dict]):
    sections = []
    for file in files:
        excerpts = "\n\n".join(file["excerpts"]) or "No relevant excerpts found."
        sections.append(f"File: {file['name']}\n{excerpts}")
    return f"Comparison question: {query}\n\n" + "\n\n".join(sections)
