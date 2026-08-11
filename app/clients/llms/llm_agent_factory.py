from .llm_clients import (
    GoogleLLMClient,
    GroqLLMClient,
    HuggingfaceLLMClient
)

from .config import LLMsProviders
from helpers.config import Settings
from models.enums import ResponsesEnum
from models.system_schemas import ComponentResult

class LLMAgentFactory:
    """
    A class used for initiating any LLM Agent using the required provider
    """
    def __init__(self, config: Settings):
        self.config = config


    def create_agent(self, provider: str) -> ComponentResult:
        """
        Creates & Returns an LLM Client

        Args:
            provider (str): the name of the LLM provider required. Allowed [groq - google - hugging_face]

        Returns:
            ComponentResult:
                if success -> content: the corresponding LLM client
                if failure -> error & respone message
        """
        if provider == LLMsProviders.GROQ_PROVIDER.value:
            try:
                return ComponentResult(
                    success = True,
                    content = GroqLLMClient(
                        api_key             = self.config.GROQ_API_KEY,
                        generation_model_id = self.config.GENERATION_MODEL_ID,
                        embedding_model_id  = None,
                        embedding_size      = None,
                    )
                )
            except Exception as e:
                return ComponentResult(
                    success = False,
                    error = e,
                    message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value
                )
        
        if provider == LLMsProviders.GOOGLE_PROVIDER.value:
            try:
                return ComponentResult(
                    success = True,
                    content = GoogleLLMClient(
                        api_key             = self.config.GOOGLE_API_KEY,
                        generation_model_id = self.config.GENERATION_MODEL_ID,
                        embedding_model_id  = self.config.EMBEDDING_MODEL_ID,
                        embedding_size      = self.config.EMBEDDING_SIZE
                    )
                )
            except Exception as e:
                return ComponentResult(
                    success = False,
                    error = e,
                    message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value
                )
        
        if provider == LLMsProviders.HUGGING_FACE.value:
            try:
                return ComponentResult(
                    success = True,
                    content = HuggingfaceLLMClient(
                        api_key             = self.config.HF_TOKEN,
                        generation_model_id = self.config.GENERATION_MODEL_ID,
                        embedding_model_id  = self.config.EMBEDDING_MODEL_ID,
                        embedding_size      = self.config.EMBEDDING_SIZE 
                    )
                )
            except Exception as e:
                return ComponentResult(
                    success = False,
                    error = e,
                    message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value
                )
    
        return ComponentResult(
            success = False,
            error = provider,
            message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value
        )
