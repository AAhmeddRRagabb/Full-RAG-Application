from models.system_schemas import RetrievedChunk

def system_prompt(*args):
    return """
You are a helpful assistant.
You will be given a list of user requirements and a combination of information that are to be useful to answer the user query.
Information are gathered from different resources (files - websearch). Each piece of information came with its relevance score to the query.

Your role is described as follows:
- you should understand the user query clearly.
- you should understand each piece of information clearly.
- use the information piece's relevance score as a guide about the most relevant pieces, but also use you relevance judge alongside it.
- finally, generate a final report clearly answers all the user requirements in a polite, clear, and professional manner.

## Rules:
- Do not invent information. If a query is not relevant to the documents, return that you need additional information.
- Your final report must address the user query and must not be a random answer. For examples:
    * If the query represents a direct question => return the direct answer.
    * If the query about a study / work plan => return a useful plan.
    and so on, but remember if the resources given does not give much info => return that you need additional info.
- Do not just tend to give long & un-sourced answers.
- In the `report` returned, only mention the required answer for the user. Do not mention from where you get the answer. For example, do not mention [from document#1, from info #1, etc..].

## Response Format:
Return your findings in the following JSON format:
{
    "report": str
    "resources": list[str] 
}

- report: the final answer you returned to the user & must answer all user requirements.
- resources: list of resources (files - websearch) that were given to you and you have found the answer in.
""".strip()


# documents summarization
def task_prompt(files_information: dict, user_requirements: list[str], websearch_info: dict) -> str:
    """
    Documents Summarization Task

    Args:
        files_information: dict[file_name => dict[info => str, relevance_score => float]]
    """
    
    # - files formatting
    files_information_str = "## Files Info:\n\n"
    for file_name, information in files_information.items():
        files_information_str += f"### File: {file_name}:\n"

        for info_idx, info_data in enumerate(information, start = 1):
            info = info_data.get('info')
            info_score = info_data.get('relevance_score')

            files_information_str += f"\t* Info NO #{info_idx} with relevance score {info_score}: {info}\n"

        files_information_str += "\n\n"

    # - web-search formatting
    web_information_str = "## Web Search Info:\n\n"
    for web_url, information in websearch_info.items():
        web_information_str += f"### Website: {web_url}:\n"

        info = information.get('info')
        info_score = information.get('relevance_score')

        web_information_str += f"\t* Info with relevance score {info_score}: {info}\n"
        web_information_str += "\n\n"


    user_requirements_str = ""
    for req in user_requirements:
        user_requirements_str += f"- {req}\n"
    

    return "\n".join([
        files_information_str,
        web_information_str,
        user_requirements_str
    ])




    


