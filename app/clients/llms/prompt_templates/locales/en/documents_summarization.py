from string import Template
from models.system_schemas import RetrievedChunk

def system_prompt(*args):
    return """
        You are a helpful assistant.
        You will be given a query and a list of documents relevant to that query.
        Your main role is to analyze all the relevant documents & extract the most useful information related to that query.

        ## Rules:
        - You should use that information as your only knowledge base.
        - Do not invent information. If a query is not relevant to the documents, return that you need additional information.
        - The documents given to you are sorted by relevance to the query, where document ###1 is the most relevant. So, give more attention to the most relevant documents.

        ## Response Format:
        Return your findings in the following JSON format:
        {
            "related_information": [
                {
                    "info": str,
                    "relevance_score": float
                }
            ],
            "need_additional_info": bool 
        }

        - related_information: list of the most relevant information peices to the query [up to 10 info pieces].
        - need_additional_info: only true if you have found that the documents are not related to the query.
    """.strip()


# documents summarization
def task_prompt(documents: list[RetrievedChunk]) -> str:
    """Documents Summarization Task"""

    documents = sorted(
        documents,
        key = lambda doc: doc.score,
        reverse = True
    )

    documents_prompt = "## Documents:\n"
    for idx, doc in enumerate(documents, start = 1):
        documents_prompt += f"### Document #{idx}: {doc.text}\n"

    return documents_prompt


def footer_prompt(query: str):
    return f"""
## Query: {query}

## Your Findings: 
"""


