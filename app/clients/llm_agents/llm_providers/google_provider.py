
from typing import Any

from .base_provider_class import BaseProviderClass
from clients.llm_agents.config import (
    LLMsGeneralEmbeddingQueryTypes,
    LLMsGoogleEmbeddingQueryTypes,
    LLMsEmbeddingModels,

    LLMsGenerationMessageTypes

    # errors
    LLMsClientConnectionError,
    LLMsEmbeddingError,
    LLMsGenerationError
)

from google.genai import Client
from google.genai.types import (
    HttpOptions,
    GenerateContentResponse,
    EmbedContentResponse,
    Content, 
    GenerateContentConfig, 
    EmbedContentConfig, 
    Part
)



class GoogleProvider(BaseProviderClass):
    """
    Using Google as a model provider
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

        self.embedding_query_types = LLMsGoogleEmbeddingQueryTypes

    
    def connect(self, api_key) -> Client:
        try:
            return Client(
            api_key = api_key,
            http_options = HttpOptions(
                timeout = 60000
            )
        )

        except Exception as e:
            raise LLMsClientConnectionError from e
    # --------------------- Embedding --------------------- #
    def get_embedding_specific_prompt_type(self, model_name: str, general_type: str) -> str:
        if model_name == LLMsEmbeddingModels.GOOGLE_EMBEDDINGS_1.value:
            if general_type == LLMsGeneralEmbeddingQueryTypes.DOCUMENT.value:
                return self.embedding_query_types.EMB1_RETRIEVAL_DOCUMENT.value
            
        return self.embedding_query_types.EMB1_RETRIEVAL_QUERY.value 

    
    # using google-embedding-1
    def _embed_text_1(self, text: list[str], prompt_type: str):
        return self.client.models.embed_content(
            model = LLMsEmbeddingModels.GOOGLE_EMBEDDING_MODEL_1.value,
            contents = text,
            config = EmbedContentConfig(
                task_type = prompt_type,
                output_dimensionality = self.embedding_size
            )
        )
    
    # using google-embedding-2
    def _format_query(self, text: str):
        return f"task: {self.embedding_query_types.EMB2_SEARCH_QUERY.value} | query: {text}"
    
    def _format_document(self, text: str, document_title: str | None = None):
        title = "none" if not document_title else document_title
        return f"title: {title} | text: {text}"

    
    def _embed_text_2(self, text: list[str], prompt_type: str, document_title: str | None = None):
        if prompt_type == LLMsGeneralEmbeddingQueryTypes.DOCUMENT.value:
            text = [self._format_document(t, document_title) for t in text]

        else:
            text = [self._format_query(t) for t in text]

        return self.client.models.embed_content(
            model = LLMsEmbeddingModels.GOOGLE_EMBEDDING_MODEL_2.value,
            contents = text,
            config = EmbedContentConfig(
                output_dimensionality = self.embedding_size
            )
        )

        
    def embed_text(
        self, 
        model_name    : str, 
        text          : str | list[str], 
        prompt_type   : str | None = None, 
        document_title: str | None = None
    ) -> list[list[float]] | None:
        """
        Embedding the give text / texts

        Args:
            model_name (str)           : google embedding model to use [gemini-embedding-001 | gemini-embedding-2]
            text (str | list[str])     : a string or a list of strings
            prompt_type (str)          : a string represents the prompt type [query - document]
            document_title (str | None)

        Returns:
            embeddings (list[[float]]): the list of each embedding list corresponding to the given texts
                                        Or None for invalid responses

        Raises:
            LLMsEmbeddingError: if error found during embedding
        """
        if isinstance(text, str):
            text = [text]

        text = [self.pre_process_input_prompt(t) for t in text]
        response: EmbedContentResponse = None
        
        # embed
        if model_name == LLMsEmbeddingModels.GOOGLE_EMBEDDINGS_2.value:
            try:
                response = self._embed_text_2(text, prompt_type, document_title)
            except Exception as e:
                raise LLMsEmbeddingError from e

        else: # embedding #1 [default]
            prompt_type = self.get_embedding_specific_prompt_type(prompt_type)
            try:
                response = self._embed_text_1(text, prompt_type)
            except Exception as e:
                raise LLMsEmbeddingError from e


        # parse response
        if not self.validate_embedding_response(response, expected_count = len(text)):
            self.logger.error(f"Invalid Embedding Response.")
            return None
        
        embeddings = []
        for embedding in response.embeddings:
            embeddings.append(embedding.values)

        return embeddings
    
    def validate_embedding_response(self, response: EmbedContentResponse, expected_count: int) -> bool:
        return (
            response 
            and response.embeddings 
            and len(response.embeddings) == expected_count 
            and all(
                response.embeddings[i].values
                for i in range(expected_count)
            )
        )

    def get_embedding_size(self, model_name: str) -> int:
        return self.embedding_size  # Google dynamically adapt embedding size
        
    
    # --------------------- Generation --------------------- #
    def _create_contents(self, user_prompt: str) -> list[Content]:
        return [
            Content(
                role = LLMsGenerationMessageTypes.GOOGLE_USER_MESSAGE.value,
                parts = [Part.from_text(text = user_prompt)]
            )
        ]
    
    def generate_text(
        self, 
        user_prompt: str, 
        chat_history: list = [], 
        max_output_tokens: int | None = None, 
        temperature: float | None = None
    ) -> str:
        contents = self._create_contents(user_prompt = user_prompt)
        chat_history.append(contents)

        try:
            response = self.client.models.generate_content(
                model    = self.generation_model_id,
                contents = chat_history,
                config   = GenerateContentConfig(
                    temperature = temperature if temperature else self.default_temperature,
                    max_output_tokens = max_output_tokens if max_output_tokens else self.default_max_output_characters
                )
            )
        except Exception as e:
            raise LLMsGenerationError from e # stopped here

        if self._validate_llm_response(response):
            return response.text
        
        raise ValueError(LLMsErrors.INVALID_MODEL_RESPONSE.value)

    # -------------------------- Validation ------------------------------- #
    def _validate_embedding_response(self, response) -> bool:
        return (
            isinstance(response, list) and
            len(response) > 0 and
            all(len(embedding.values) > 0 for embedding in response)
        )


    def _validate_llm_response(self, response):
        return (
            response and
            response.text
        )
    
       
