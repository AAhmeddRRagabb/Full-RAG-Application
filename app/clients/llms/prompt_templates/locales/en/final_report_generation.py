from models.system_schemas import RetrievedChunk

def system_prompt(*args):
    return """
        You are a helpful assistant.
        You will be given a user query and a combination of information that are to be useful to answer the user query.
        Information are gathered from different resources (files - websearch). Each piece of information came with its relevance score to the query.

        Your role is described as follows:
        - you should understand the user query clearly.
        - you should understand each piece of information clearly.
        - use the information piece's relevance score as a guide about the most relevant pieces, but also use you relevance judge alongside it.
        - finally, generate a final report clearly answers the user query in a polite, clear, and professional manner.

        ## Rules:
        - Do not invent information. If a query is not relevant to the documents, return that you need additional information.
        - Your final report must address the user query and must not be a random answer. For examples:
            * If the query represents a direct question => return the direct answer.
            * If the query about a study / work plan => return a useful plan.
            and so on, but remember if the resources given does not give much info => return that you need additional info.
        - Do not just tend to give long & un-sourced answers.
    """.strip()


# documents summarization
def task_prompt(information_resources: list[list[dict[str, str | float]]]) -> str:
    """Documents Summarization Task"""

    resources_prompt = "## Information Resources:\n"
    for idx, resource in enumerate(information_resources, start = 1):
        resources_prompt += f"### Resource_#{idx}:\n"

        for info_idx, info_data in enumerate(resource, start = 1):
            info = info_data.get('info')
            info_score = info_data.get('relevance_score')

            resources_prompt += f"\t* Info_#{info_idx} with relevance score {info_score} >> {info}\n"

        resources_prompt += "\n"


    return resources_prompt


def footer_prompt(query: str):
    return f"""
## Query: {query}

## Final Report: 
"""


