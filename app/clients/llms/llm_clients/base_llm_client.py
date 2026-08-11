from abc import abstractmethod
import logging
from typing import Any

from models.system_schemas import ComponentResult

class BaseLLMClient:
    """
    A base provider class used as a parent for any LLM Provider
    """
    def __init__(
        self,
        api_key                  : str,
        generation_model_id      : str,
        embedding_model_id       : str,
        embedding_size           : int,
        max_input_tokens         : int = 1000,
        api_url                  : str | None = None,
        default_max_output_tokens: int = 1000,
        default_temperature      : float = 0.1
    ):
        # setup
        self.max_input_tokens = max_input_tokens
        self.default_max_output_tokens = default_max_output_tokens
        self.default_temperature = default_temperature

        self.generation_model_id = generation_model_id
        self.embedding_model_id = embedding_model_id
        self.embedding_size = embedding_size

        self.api_url = api_url

        self.logger = logging.getLogger("uvicorn")
        self.client = self.connect(api_key = api_key)


    @abstractmethod
    def connect(self, api_key: str):
        pass

    def disconnect(self):
        try:
            self.client.close()
        except:
            pass

        self.client = None

    def _return_success(self, content: Any | None = None, message: str | None = None) -> ComponentResult:
        return ComponentResult(
            success = True,
            content = content,
            message = message
        )

    def _return_failure(self, error: Any | None = None, message: str | None = None) -> ComponentResult:
        return ComponentResult(
            success = False,
            error = error,
            message = message
        )

    
    # setting CFG
    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id


    def set_embedding_config(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size


    # pre-processing
    def pre_process_input_prompt(self, prompt: str) -> str:
        """
        Ensure that the input length is within the permitted range.
        """
        if len(prompt) > self.max_input_tokens:
            self.logger.info(
                "Prompt has exceeded the max input tokens\n"
                f"- Prompt: {prompt[:50]}...\n"
                f"- Prompt Length: {len(prompt)}\n"
                f"- Max Allowed Input Length: {self.max_input_tokens}\n"
                ">>> Prompt will be truncated <<<\n\n"
            )

            return prompt[:self.max_input_tokens]
        
        return prompt


    # --------------------------------------------------------- Embedding ------------------------------------------------------ #
    @abstractmethod
    def get_embedding_specific_prompt_type(self, general_type: str) -> str:
        """Turning general prompt type to provider-specific prompt type"""
        pass
    
    @abstractmethod
    def embed_text(
        self, 
        text          : str | list[str], 
        prompt_type   : str | None = None, 
        document_title: str | None = None
    ) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: list of embeddings
                if failure -> error & respone message
        """
        pass

    @abstractmethod
    def validate_embedding_response(self, response) -> bool:
        pass

    @abstractmethod
    def get_embedding_size(self, model_name: str) -> int:
        pass

    # --------------------------------------------------------- Generation ------------------------------------------------------ #
    @abstractmethod
    def generate_text(
        self, 
        user_prompt: str, 
        chat_history: list = [], 
        max_output_tokens: int | None = None, 
        temperature: float | None = None
    ) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: generated text
                if failure -> error & respone message
        """
        pass    

    @abstractmethod
    def validate_generation_response(self, response) -> bool:
        pass

    @abstractmethod
    def create_prompt(self, prompt: str, role: str):
        pass

