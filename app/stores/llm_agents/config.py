from enum import Enum


class LLMsProviders(Enum):
    GROQ_PROVIDER   = "groq"
    GOOGLE_PROVIDER = "google_genai"
    HUGGING_FACE    = "hugging_face"
    OPEN_AI         = "openai"


class LLMsErrors(Enum):
    MODEL_IS_NOT_AVAILABLE = "Model required is not available"
    INVALID_MODEL_RESPONSE = "Invalid model response, please try again."



# Embedding Query Types
class LLMsGeneralEmbeddingQueryTypes(Enum):
    SEARCH_QUERY = "query"
    DOCUMENT = "document"


class LLMsGoogleEmbeddingQueryTypes(Enum):
    EMB1_RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    EMB1_RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"
    EMB2_SEARCH_QUERY = "search result"



# Generation Message Types
class LLMsGenerationMessageTypes(Enum):
    OPENAI_SYSTEM_MESSAGE    = "system"
    OPENAI_USER_MESSAGE      = "user"
    OPENAI_ASSISTANT_MESSAGE = "assistant"


    GROQ_SYSTEM_MESSAGE    = "system"
    GROQ_USER_MESSAGE      = "user"
    GROQ_ASSISTANT_MESSAGE = "assistant"

    GOOGLE_SYSTEM_MESSAGE    = "system"
    GOOGLE_USER_MESSAGE      = "user"
    GOOGLE_ASSISTANT_MESSAGE = "model"

    HF_SYSTEM_MESSAGE    = "system"
    HF_USER_MESSAGE      = "user"
    HF_ASSISTANT_MESSAGE = "assistant"


# Models
class LLMsEmbeddingModels(Enum):
    GOOGLE_EMBEDDINGS_1 = "gemini-embedding-1"
    GOOGLE_EMBEDDINGS_2 = "gemini-embedding-2"