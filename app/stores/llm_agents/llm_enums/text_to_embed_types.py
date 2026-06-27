from enum import Enum


class TextTypesEnum(Enum):
    SEARCH_QUERY = "query"
    DOCUMENT = "document"



class GoogleTaskTypes(Enum):
    EMB1_RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    EMB1_RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"
    EMB2_SEARCH_QUERY = "search result"