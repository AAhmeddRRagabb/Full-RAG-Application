from .base_provider_class import BaseProviderClass
from stores.llm_agents.llm_enums import OpenAIMessageRolesEnum, LLM_Errors_Enum

from openai import OpenAI
import logging


class OpenAIProvider(BaseProviderClass):
    """
    Using OpenAI as a model provider
    """

    def __init__(
        self,
        api_key: str,
        api_url: str,
        generation_model_id: str,
        embedding_model_id: str,
        embedding_size: int,
        default_max_input_characters: int = 1000,
        default_max_output_characters: int = 1000,
        default_temperature: float = 0.1
    ) -> None:

        self.api_url = api_url

        super().__init__(
            api_key=api_key,
            generation_model_id=generation_model_id,
            embedding_model_id=embedding_model_id,
            embedding_size=embedding_size,
            default_max_input_characters=default_max_input_characters,
            default_max_output_characters=default_max_output_characters,
            default_temperature=default_temperature,
        )

        self.message_roles_enum = OpenAIMessageRolesEnum
        self.logger = logging.getLogger(__name__)

    def init_client(self, api_key: str) -> OpenAI:
        return OpenAI(
            api_key=api_key,
            base_url=self.api_url if self.api_url and len(self.api_url) else None
        )

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size



    # --------------------- Embedding --------------------- #
    def embed_text(self, text: str, document_type: str = None):
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for OpenAI was not set")
            return None

        response = self.client.embeddings.create(
            model=self.embedding_model_id,
            input=text,
        )

        if self._validate_embedding_response(response):
            return response.data[0].embedding

        self.logger.error("Error while embedding text with OpenAI")
        return None

    def _validate_embedding_response(self, response) -> bool:
        return (
            response
            and response.data
            and len(response.data) > 0
            and response.data[0].embedding
        )

    # --------------------- Generation --------------------- #
    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": self._process_text_length(prompt)
        }

    def generate_text(
        self,
        prompt: str,
        chat_history: list = [],
        max_output_tokens: int = None,
        temperature: float = None
    ):
        if not self.client:
            self.logger.error("OpenAI client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for OpenAI was not set")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_max_output_characters
        temperature = temperature if temperature else self.default_temperature

        chat_history.append(
            self.construct_prompt(
                prompt=prompt,
                role=self.message_roles_enum.USER_MESSAGE.value
            )
        )

        response = self.client.chat.completions.create(
            model=self.generation_model_id,
            messages=chat_history,
            max_tokens=max_output_tokens,
            temperature=temperature
        )

        if self._validate_llm_response(response):
            return response.choices[0].message.content

        self.logger.error("Error while generating text with OpenAI")
        return None

    def _validate_llm_response(self, response) -> bool:
        return (
            response
            and response.choices
            and len(response.choices) > 0
            and response.choices[0].message
        )