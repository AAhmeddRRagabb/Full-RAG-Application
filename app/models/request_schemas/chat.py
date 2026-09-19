from pydantic import BaseModel


class ANSWER_QUERY_REQUEST(BaseModel):
    query: str
    retrieve_limit: int = 5
    files_to_use: list[str] = []