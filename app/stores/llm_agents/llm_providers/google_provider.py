
from google.genai import Client
from google.genai.types import GenerateContentResponse, Content, GenerateContentConfig, EmbedContentConfig, Part
from typing import Any
from .base_provider_class import BaseProviderClass

from llm_enums import TextTypesEnum, GoogleTaskTypes, GoogleEmbeddingModelsEnum, LLM_Errors_Enum, GoogleMessageRolesEnum

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

    
    def init_client(self, api_key: str) -> Client:
        return Client(
            api_key = api_key
        )
    # --------------------- Embedding --------------------- #
    def embed_text(self, text: str, text_type: str, document_title: str | None = None):
        text = self._process_text_length(text)
        if self.embedding_model_id == GoogleEmbeddingModelsEnum.EMBEDDINGS_1.value:
            response = self._embed_text_1(text, text_type)
        
        elif self.embedding_model_id == GoogleEmbeddingModelsEnum.EMBEDDINGS_2.value:
            response = self._embed_text_2(text, text_type, document_title)

        else:
            raise ValueError(LLM_Errors_Enum.MODEL_IS_NOT_AVAILABLE.value)
        
        if not self._validate_embedding_response(response):
            raise ValueError(LLM_Errors_Enum.INVALID_MODEL_RESPONSE.value)
        

        return response.embeddings
        
        

    # using google-embeding-1
    def _get_task_type(self, text_type: str) -> str:
        if text_type == TextTypesEnum.SEARCH_QUERY.value:
            return GoogleTaskTypes.EMB1_RETRIEVAL_QUERY.value
        
        if text_type == TextTypesEnum.DOCUMENT.value:
            return GoogleTaskTypes.EMB1_RETRIEVAL_DOCUMENT.value
        
        return None
        

    def _embed_text_1(self, text: str, text_type: str):
        task_type = self._get_task_type(text_type)

        if not task_type:
            return None
        
        return self.client.models.embed_content(
            model = self.embedding_model_id,
            contents = text,
            config = EmbedContentConfig(
                task_type = task_type,
                output_dimensionality = self.embedding_size
            )
        )
    

    # using google-embedding-2
    def _format_query(self, text: str):
        return f"task: {GoogleTaskTypes.EMB2_SEARCH_QUERY.value} | query: {text}"
    
    def _format_document(self, text: str, document_title: str | None = None):
        title = "none" if not document_title else document_title
        return f"title: {title} | text: {text}"
    
    def _embed_text_2(self, text: str, text_type: str, document_title: str | None = None):
        if text_type == TextTypesEnum.SEARCH_QUERY.value:
            text = self._format_query(text)
        
        elif text_type == TextTypesEnum.DOCUMENT.value:
            text = self._format_document(text, document_title)

        else:
            return None

        return self.client.models.embed_content(
            model = self.embedding_model_id,
            contents = text,
            config = EmbedContentConfig(
                output_dimensionality = self.embedding_size
            )
        )
    
    # --------------------- Generation --------------------- #
    def construct_prompt(self, prompt: str, role: str):
        return [
            Content(
                role = role,
                parts = [
                    Part.from_text(text = prompt)
                ]
            )
        ]
    
    def generate_text(
        self, 
        user_prompt: str, 
        chat_history: list = [], 
        max_output_tokens: int | None = None, 
        temperature: float | None = None
    ) -> str:
        user_prompt = self.construct_prompt(query = user_prompt)
        chat_history.append(user_prompt)

        response = self.client.models.generate_content(
            model    = self.generation_model_id,
            contents = chat_history,
            config   = GenerateContentConfig(
                temperature = temperature if temperature else self.default_temperature,
                max_output_tokens = max_output_tokens if max_output_tokens else self.default_max_output_characters
            )
        )

        if self._validate_llm_response(response):
            return response.text
        
        raise ValueError(LLM_Errors_Enum.INVALID_MODEL_RESPONSE.value)

    # -------------------------- Validation ------------------------------- #
    def _validate_embedding_response(self, response) -> bool:
        return (
            response and
            response.embeddings
        )


    def _validate_llm_response(self, response):
        return (
            response and
            response.text
        )
    
       
