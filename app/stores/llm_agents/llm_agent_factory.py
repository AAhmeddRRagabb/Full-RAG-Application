from .llm_providers import GroqProvider, GoogleProvider
from .llm_enums import ProviderNamesEnum
from helpers.config import Settings

class LLMAgentFactory:
    """
    A class used for initiating any LLM Agent using the required provider
    """
    def __init__(self, config: Settings):
        self.config = config


    def create_agent(self, provider: str) -> GroqProvider | GoogleProvider:
        if provider == ProviderNamesEnum.GROQ_PROVIDER.value:
            return GroqProvider(
                api_key = self.config.GROQ_API_KEY,
                generation_model_id = self.config.GENERATION_MODEL_ID,
                embedding_model_id = None,
                embedding_size = None,
            )
        
        if provider == ProviderNamesEnum.GOOGLE_PROVIDER.value:
            return GoogleProvider(
                api_key = self.config.GOOGLE_API_KEY,
                generation_model_id = self.config.GENERATION_MODEL_ID,
                embedding_model_id = self.config.EMBEDDING_MODEL_ID,
                embedding_size = self.config.EMBEDDING_SIZE
            )
        

        raise NotImplementedError
