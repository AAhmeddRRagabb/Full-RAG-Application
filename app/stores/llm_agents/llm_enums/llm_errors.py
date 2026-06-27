from enum import Enum


class LLM_Errors_Enum(Enum):
    MODEL_IS_NOT_AVAILABLE = "Model required is not available"
    INVALID_MODEL_RESPONSE = "Invalid model response, please try again."