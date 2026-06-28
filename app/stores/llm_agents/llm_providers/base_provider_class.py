from abc import abstractmethod
import logging

class BaseProviderClass:
    """
    A base provider class used as a parent for any LLM Provider
    """
    def __init__(
        self,
        api_key: str,
        generation_model_id: str,
        embedding_model_id: str,
        embedding_size: int,
        default_max_input_characters: int = 1000,
        default_max_output_characters: int = 1000,
        default_temperature: float = 0.1
    ):
        # setup
        self.default_max_input_characters = default_max_input_characters
        self.default_max_output_characters = default_max_output_characters
        self.default_temperature = default_temperature

        self.generation_model_id = generation_model_id
        self.embedding_model_id = embedding_model_id
        self.embedding_size = embedding_size

        self.logger = logging.getLogger(__name__)
        self.client = self.init_client(api_key = api_key)

    @abstractmethod
    def init_client(self, api_key: str):
        pass

    
    # setting CFG
    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_config(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size


    # embedding
    @abstractmethod
    def embed_text(self, text: str, text_type: str):
        """
        Args:
            text: the text to embed
            text_type: string determines whether the text is for the search query or the document to retrieve
        """
        pass

    # generation
    @abstractmethod
    def construct_prompt(self, prompt: str, role: str):
        pass

    @abstractmethod
    def generate_text(
        self, 
        user_prompt: str, 
        chat_history: list = [], 
        max_output_tokens: int | None = None, 
        temperature: float | None = None
    ):
        pass

    # # validation
    def _process_text_length(self, prompt: str, return_error: bool = False) -> str:
        return prompt
    #     if len(prompt) > self.default_max_input_characters:
    #         if return_error:
    #             raise ValueError
            
    #         prompt = prompt[:self.default_max_input_characters].strip()
        
    #     return prompt
    
    @abstractmethod
    def _validate_llm_response(self, response) -> bool:
        pass

    @abstractmethod
    def _validate_embedding_response(self, response) -> bool:
        pass


