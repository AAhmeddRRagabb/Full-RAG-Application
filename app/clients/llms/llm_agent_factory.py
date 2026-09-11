from .llm_clients import (
    GoogleLLMClient,
    GroqLLMClient,
    HuggingfaceLLMClient
)

from .config import LLMsProviders
from helpers.config import Settings
from models.enums import ResponsesEnum

class LLMAgentFactory:
    """
    A class used for initiating an LLM Agent using the required provider
    """
    def __init__(self, config: Settings):
        self.config = config


    def create_agent(self, provider: str) -> GoogleLLMClient | GroqLLMClient | HuggingfaceLLMClient | None:
        """
        Creates & Returns an LLM Client

        Args:
            provider (str): the name of the LLM provider required. Allowed [groq - google - hugging_face]

        Returns:
            if success -> the required LLM Client  
            if failure -> None
        """
        
        if provider == LLMsProviders.GROQ_PROVIDER.value:
            return GroqLLMClient(
                api_key             = self.config.GROQ_API_KEY,
                generation_model_id = self.config.GENERATION_MODEL_ID,
                embedding_model_id  = None,
                embedding_size      = None,
            )
                

        
        if provider == LLMsProviders.GOOGLE_PROVIDER.value:
            return GoogleLLMClient(
                api_key             = self.config.GOOGLE_API_KEY,
                generation_model_id = self.config.GENERATION_MODEL_ID,
                embedding_model_id  = self.config.EMBEDDING_MODEL_ID,
                embedding_size      = self.config.EMBEDDING_SIZE
            )
                

        if provider == LLMsProviders.HUGGING_FACE.value:
            return HuggingfaceLLMClient(
                api_key             = self.config.HF_TOKEN,
                generation_model_id = self.config.GENERATION_MODEL_ID,
                embedding_model_id  = self.config.EMBEDDING_MODEL_ID,
                embedding_size      = self.config.EMBEDDING_SIZE 
            )

    
        return None
