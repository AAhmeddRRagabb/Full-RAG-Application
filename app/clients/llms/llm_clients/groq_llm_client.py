from clients.llms.config import (
    LLMsGenerationMessageTypes,

    LLMsClientConnectionError
)
from models.enums import ResponsesEnum
from models.system_schemas import ComponentResult

from .base_llm_client import BaseLLMClient
from groq import Groq
from groq.types.chat import ChatCompletion

class GroqLLMClient(BaseLLMClient):
    """
    Using Groq as a model provider

    """
    def __init__(
        self,
        api_key: str,
        generation_model_id: str,
        embedding_model_id: str,
        embedding_size: int,
        api_url: str | None = None,
        max_input_tokens: int = 1000,
        default_max_output_tokens: int = 1000,
        default_temperature: float = 0.1
    ) -> None:
        
        super().__init__(
            api_key                   = api_key,
            generation_model_id       = generation_model_id,
            embedding_model_id        = embedding_model_id,
            embedding_size            = embedding_size,
            max_input_tokens          = max_input_tokens,
            default_max_output_tokens = default_max_output_tokens,
            default_temperature       = default_temperature,
            api_url                   = api_url
        )

    
    def connect(self, api_key: str) -> Groq:
        try:
            return Groq(
                api_key = api_key,
                timeout = 60
            )
        
        except Exception as e:
            raise LLMsClientConnectionError from e
    
    # --------------------- Embedding --------------------- #
    def get_embedding_specific_prompt_type(self, general_type: str) -> str:
            raise NotImplementedError("Groq does not support embeddings.")
        
    def embed_text(
        self, 
        text          : str | list[str], 
        prompt_type   : str | None = None, 
        document_title: str | None = None
    ):
        raise NotImplementedError("Groq does not support embeddings.")

    def validate_embedding_response(self, response) -> bool:
        raise NotImplementedError("Groq does not support embeddings.")

    def get_embedding_size(self, model_name):
        raise NotImplementedError("Groq does not support embeddings.")

    
    # --------------------- Generation --------------------- #

    def create_prompt(self, prompt: str, role: str):
        return {
            'content': prompt,
            'role'   : role
        }


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
        
        messages = self.create_prompt(
            prompt = user_prompt,
            role   = LLMsGenerationMessageTypes.GROQ_USER_MESSAGE.value
        )

        if chat_history is None:
            chat_history = []

        chat_history.append(messages)
        response: ChatCompletion = None
        try:
            response = self.client.chat.completions.create(
                messages    = chat_history,
                model       = self.generation_model_id,
                stream      = False,
                temperature = temperature if temperature else self.default_temperature,
                max_tokens  = max_output_tokens if max_output_tokens else self.default_max_output_tokens
            )

        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value)
                
        if not self.validate_generation_response(response):
            self.logger.error("Invalid Generation Response")
            return self._return_failure(message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value)
    
        return self._return_success(content = response.choices[0].message.content)


    def validate_generation_response(self, response: ChatCompletion) -> bool:
        return (
            response and
            response.choices and
            len(response.choices) > 0 and
            response.choices[0] and 
            response.choices[0].message and
            response.choices[0].message.content
        )
