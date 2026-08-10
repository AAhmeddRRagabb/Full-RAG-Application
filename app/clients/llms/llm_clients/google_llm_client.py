

from .base_llm_client import BaseLLMClient
from clients.llms.config import (
    LLMsGeneralEmbeddingQueryTypes,
    LLMsGoogleEmbeddingQueryTypes,
    LLMsEmbeddingModels,

    LLMsGenerationMessageTypes,

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


class GoogleLLMClient(BaseLLMClient):
    """
    Using Google as a model provider
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
            model = LLMsEmbeddingModels.GOOGLE_EMBEDDINGS_1.value,
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
            model = LLMsEmbeddingModels.GOOGLE_EMBEDDINGS_2.value,
            contents = text,
            config = EmbedContentConfig(
                output_dimensionality = self.embedding_size
            )
        )

        
    def embed_text(
        self, 
        text          : str | list[str], 
        prompt_type   : str | None = None, 
        document_title: str | None = None
    ) -> list[list[float]] | None:
        """
        Embedding the give text / texts

        Args:
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
        if self.embedding_model_id == LLMsEmbeddingModels.GOOGLE_EMBEDDINGS_2.value:
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
    def create_prompt(self, prompt: str, role: str):
        return [
            Content(
                role = role,
                parts = [Part.from_text(text = prompt)]
            )
        ]
    
    def generate_text(
        self, 
        user_prompt: str, 
        chat_history: list = [], 
        max_output_tokens: int | None = None, 
        temperature: float | None = None
    ) -> str:
        
        """
        Generate text based on the given inputs:

        Args:
            user_prompt (str)      : string query
            chat_history (list)    : previous chat history [optional]
            max_output_tokens (int): max number of output tokens required
            temperature (flaot)    : generation temperature
        
        Returns:
            response:
                - the whole response (GenerateContentResponse) if (return_whole_response == True)
                - None if invalid response
                - the text part otherwise
        
        Raises:
            LLMsGenerationError: if error found during generation
        """

        contents = self.create_prompt(
            prompt = self.pre_process_input_prompt(user_prompt),
            role   = LLMsGenerationMessageTypes.GOOGLE_USER_MESSAGE
        )
        
        chat_history.append(contents)

        try:
            response = self.client.models.generate_content(
                model    = self.generation_model_id,
                contents = chat_history,
                config   = GenerateContentConfig(
                    temperature       = temperature if temperature else self.default_temperature,
                    max_output_tokens = max_output_tokens if max_output_tokens else self.default_max_output_tokens
                )
            )

        except Exception as e:
            raise LLMsGenerationError from e

        if not self.validate_generation_response(response):
            self.logger.error("Invalid Generation Response")
            return None

        
        return response.text
 
    def validate_generation_response(self, response: GenerateContentResponse ) -> bool:
        return (
            response and
            response.text
        )
    
       
