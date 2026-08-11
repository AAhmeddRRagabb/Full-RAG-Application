
from clients.llms.config import (
    LLMsGeneralEmbeddingQueryTypes,
    LLMsHuggingfaceEmbeddingQueryTypes,
    LLMsGenerationMessageTypes,
    LLMsClientConnectionError
)
from models.enums import ResponsesEnum
from models.system_schemas import ComponentResult

import numpy as np
from .base_llm_client import BaseLLMClient
from groq.types.chat import ChatCompletion
from huggingface_hub import InferenceClient


class HuggingfaceLLMClient(BaseLLMClient):
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

        self.embedding_query_types = LLMsHuggingfaceEmbeddingQueryTypes
    
    def connect(self, api_key: str) -> InferenceClient:
        try:
            return InferenceClient(
                api_key = api_key,
                provider = "auto",
                timeout = 60
            )

        except Exception as e:
            raise LLMsClientConnectionError from e
        
    
    # --------------------- Embedding --------------------- #
    def get_embedding_specific_prompt_type(self, general_type: str) -> str:
        if general_type == LLMsGeneralEmbeddingQueryTypes.DOCUMENT.value:
            return self.embedding_query_types.DOCUMENT.value
        
        return self.embedding_query_types.QUERY.value
            
        
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

        if isinstance(text, str):
            text = [text]

        text = [self.pre_process_input_prompt(t) for t in text]
        response: np.ndarray = None

        # embed
        try:
            response = self.client.feature_extraction(
                text = text,
                model = self.embedding_model_id,
                normalize = True,
                prompt_name = self.get_embedding_specific_prompt_type(prompt_type),
                dimensions = self.embedding_size
            ).tolist()

            embeddings = np.asarray(response, dtype = np.float32).tolist()
            
        except Exception as e:
            return self._return_failure(error = e, message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value)

        # parse
        if not self.validate_embedding_response(embeddings,expected_count = len(text)):
            self.logger.error(f"Invalid Embedding Response.")
            return self._return_failure(message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value)
        
        return self._return_success(content = embeddings)


    def validate_embedding_response(self, response: list[list[float]], expected_count: int) -> bool:
        return (
            isinstance(response, list)
            and len(response) == expected_count
            and all(
                isinstance(embedding, list)
                for embedding in response
            )
        )

    def get_embedding_size(self, model_name: str) -> int:
        _response = self.embed_text(
            text = "Hello",
        ).content[0]

        return len(_response)

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
            role   = LLMsGenerationMessageTypes.HF_USER_MESSAGE.value
        )

        if chat_history is None:
            chat_history = []
        chat_history.append(messages)


        response: ChatCompletion = None

        try:
            response = self.client.chat_completion(
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
