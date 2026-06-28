
from groq.types.chat import ChatCompletion
from .base_provider_class import BaseProviderClass
from stores.llm_agents.llm_enums import HuggingFaceMessageRolesEnum, LLM_Errors_Enum

from huggingface_hub import InferenceClient

class HuggingFaceProvider(BaseProviderClass):
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

        self.message_roles_enum = HuggingFaceMessageRolesEnum
    
    def init_client(self, api_key: str) -> InferenceClient:
        return InferenceClient(
            api_key = api_key,
            provider = "auto"
        )
    
    # --------------------- Embedding --------------------- #
    def embed_text(self, text: str, text_type: str):
        embedding = self.client.feature_extraction(
            text = text,
            model = self.embedding_model_id,
            normalize = True
        ).tolist()

        if len(embedding) == 1 and isinstance(embedding[0], list):
            embedding = embedding[0]

        if self._validate_embedding_response(embedding):
            return embedding

        raise ValueError(LLM_Errors_Enum.INVALID_MODEL_RESPONSE.value)

    

    def _validate_embedding_response(self, response) -> bool:
        return (
            isinstance(response, list)
            and len(response) > 0
            and all(isinstance(x, float) for x in response)
        )
    

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        processed_texts = [
            self._process_text_length(text)
            for text in texts
        ]

        response = self.client.feature_extraction(
            text=processed_texts,
            model=self.embedding_model_id,
            normalize=True,
        )

        vectors = response.tolist()

        if self._validate_many_embedding_response(vectors):
            return vectors

        raise ValueError(LLM_Errors_Enum.INVALID_MODEL_RESPONSE.value)
    
    def _validate_many_embedding_response(self, response) -> bool:
        return (
            isinstance(response, list)
            and len(response) > 0
            and all(isinstance(vector, list) for vector in response)
            and all(
                all(isinstance(x, float) for x in vector)
                for vector in response
            )
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
        user_prompt = self.construct_prompt(prompt = user_prompt, role = HuggingFaceMessageRolesEnum.USER_MESSAGE.value)

        if chat_history is None:
            chat_history = []
        chat_history.append(user_prompt)

        response = self.client.chat_completion(
            messages = chat_history,
            model = self.generation_model_id,
            stream = False,
            temperature = temperature if temperature else self.default_temperature,
            max_tokens = max_output_tokens if max_output_tokens else self.default_max_output_characters
        )
        
        if self._validate_llm_response(response):
            return response.choices[0].message.content
    
        raise ValueError(LLM_Errors_Enum.INVALID_MODEL_RESPONSE.value)


    def _validate_llm_response(self, response: ChatCompletion) -> bool:
        return (
            response and
            response.choices and
            len(response.choices) > 0 and
            response.choices[0].message and
            response.choices[0].message.content
        )
