
from groq import Groq
from groq.types.chat import ChatCompletion
from .base_provider_class import BaseProviderClass
from stores.llm_agents.llm_enums import GroqMessageRolesEnum, LLM_Errors_Enum

class GroqProvider(BaseProviderClass):
    """
    Using Groq as a model provider

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
    ) -> None:
        
        super().__init__(
            api_key = api_key,
            generation_model_id = generation_model_id,
            embedding_model_id = embedding_model_id,
            embedding_size = embedding_size,
            default_max_input_characters = default_max_input_characters,
            default_max_output_characters = default_max_output_characters,
            default_temperature = default_temperature,
        )

        self.message_roles_enum = GroqMessageRolesEnum
    
    def init_client(self, api_key: str) -> Groq:
        return Groq(
            api_key = api_key
        )
    
    # --------------------- Embedding --------------------- #
    def embed_text(self, text: str | list[str], text_type: str):
        if not self.client:
            self.logger.error("Groq client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for Groq was not set")
            return None

        is_single_text = isinstance(text, str)
        input_text = [text] if is_single_text else text
        input_text = [
            self._process_text_length(t)
            for t in input_text
        ]

        response = self.client.embeddings.create(
            model = self.embedding_model_id,
            input = input_text,
        )

        if self._validate_embedding_response(response):
            embeddings = [
                item.embedding
                for item in sorted(response.data, key = lambda item: item.index)
            ]
            return embeddings[0] if is_single_text else embeddings

        raise ValueError(LLM_Errors_Enum.INVALID_MODEL_RESPONSE.value)
    
    def _validate_embedding_response(self, response):
        return (
            response and
            response.data and
            len(response.data) > 0 and
            all(item.embedding for item in response.data)
        )
    # --------------------- Generation --------------------- #
    def construct_prompt(self, prompt: str, role: str) -> dict[str, str]:
        return {
            "role": role,
            "content": self._process_text_length(prompt)
        }

    def generate_text(
        self, 
        user_prompt: str, 
        chat_history: list = [], 
        max_output_tokens: int | None = None, 
        temperature: float | None = None
    ) -> str:
        user_prompt = self.construct_prompt(prompt = user_prompt, role = GroqMessageRolesEnum.USER_MESSAGE.value)

        if chat_history is None:
            chat_history = []

        chat_history.append(user_prompt)

        response = self.client.chat.completions.create(
            messages = chat_history,
            model = self.generation_model_id,
            stream = False,
            temperature = temperature if temperature else self.default_temperature,
            max_tokens = max_output_tokens if max_output_tokens else self.default_max_output_characters
        )
        
        if self._validate_llm_response(response):
            return response.choices[0].message.content
    
        raise ValueError(LLM_Errors_Enum.INVALID_MODEL_RESPONSE.value)
    # --------------------- Validation ------------------ #
    def _validate_llm_response(self, response: ChatCompletion) -> bool:
        return (
            response and
            response.choices and
            len(response.choices) > 0 and
            response.choices[0].message and
            response.choices[0].message.content
        )
