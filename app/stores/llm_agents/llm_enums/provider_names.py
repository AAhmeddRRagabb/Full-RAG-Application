from enum import Enum

class ProviderNamesEnum(Enum):
    GROQ_PROVIDER = "groq"
    GOOGLE_PROVIDER = "google_genai"
    HUGGING_FACE = "hugging_face"
    OPEN_AI = "openai"