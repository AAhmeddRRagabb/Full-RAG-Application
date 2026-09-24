from string import Template
from models.system_schemas import RetrievedChunk

def system_prompt(*args):
    return """
You are a helpful assistant.
You will be given a query and a list of search web-search info relevant to that query.
The web-search info are gathered using a Web Search Tool.
Your main role is to analyze all the relevant info & extract the most useful information related to that query.

## Rules:
- You should use that information as your only knowledge base.
- Do not invent information. If a query is not relevant to the documents, return that you need additional information.
- The info given to you are sorted by relevance to the query, where document ###1 is the most relevant. So, give more attention to the most relevant documents.
- The info may have publish-date. If a publish date given, give more attention to the most recent information.

## Response Format:
Return your findings in the following JSON format:
{
    "related_information": [
        {
            "info": str,
            "relevance_score": float,
            "url" : str
        }
    ],
    "need_additional_info": bool 
}

- related_information: list of the most relevant information peices to the query [up to 10 info pieces].
- need_additional_info: only true if you have found that the documents are not related to the query.
- url: the url from where the info gathered [it is given to you].
""".strip()


# documents summarization
def task_prompt(query: str, websearch_results: list[dict]) -> str:
    """Documents Summarization Task"""

    websearch_results = sorted(
        websearch_results,
        key = lambda doc: doc.get('score'),
        reverse = True
    )

    does_have_date = all([
        s.get('published_date', False)
        for s in websearch_results
    ])


    websearch_results_str = "## WebSearch Results:\n\n"
    for website in websearch_results:
        if does_have_date:
            websearch_results_str += f"### Website: [{website.get("url")} - Relevance Score: {website.get('score')} - Publish Date: {website.get('published_date')}]\n"
        else:
            websearch_results_str += f"### Website: [{website.get("url")} - Relevance Score: {website.get('score')}]\n"

        websearch_results_str += f"{website.get('content')}\n\n"


    footer_prompt = f"""
## Query: {query}

## Your Findings: 
""".strip()

    return "\n".join([
        websearch_results_str,
        footer_prompt
    ])





