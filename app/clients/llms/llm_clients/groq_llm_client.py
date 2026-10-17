from models.db_schemas import Message
from clients.llms.config import LLMsGenerationMessageTypes


from .base_llm_client import BaseLLMClient
from groq import Groq
from groq.types.chat import ChatCompletion
from core.helpers import log_llm_error

class GroqLLMClient(BaseLLMClient):
    def __init__(
        self,
        api_key                  : str,
        generation_model_id      : str,
        embedding_model_id       : str,
        embedding_size           : int,
        generation_system_prompt : str | None = None,
        reasoning_effort        : str | None = None,
        api_url                  : str | None = None,
        max_input_tokens         : int = 1000,
        default_max_output_tokens: int = 1000,
        default_temperature      : float = 0.1
    ) -> None:
        
        super().__init__(
            api_key                   = api_key,
            generation_model_id       = generation_model_id,
            embedding_model_id        = embedding_model_id,
            embedding_size            = embedding_size,
            generation_system_prompt  = generation_system_prompt,
            max_input_tokens          = max_input_tokens,
            default_max_output_tokens = default_max_output_tokens,
            default_temperature       = default_temperature,
            api_url                   = api_url
        )
        self.reasoning_effort = reasoning_effort

    
    def connect(self, api_key: str) -> Groq:
        try:
            return Groq(
                api_key = api_key,
                timeout = 60
            )
        
        except Exception as e:
            self.logger.error(f"Error While Initiating LLM Client: {e}")
            return None
    
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
        user_prompt      : str,
        messages         : list[Message] | None = None,  
        max_output_tokens: int | None = None, 
        temperature      : float | None = None
    ) -> str | None:
        
        """
        Args:
            user_prompt  (str)
            messages (list[Message])
            max_output_tokens (int)
            temperature (float)

        Returns:
            if success -> model response
            if failure -> None
        """
        messages = [
            self.create_prompt(
                prompt = m.content,
                role = m.role
            ) for m in messages
        ] if messages else []

        system_message = self.create_prompt(
            prompt = self.generation_system_prompt,
            role = LLMsGenerationMessageTypes.GROQ_SYSTEM_MESSAGE.value,
        )
        
        user_message = self.create_prompt(
            prompt = user_prompt,
            role   = LLMsGenerationMessageTypes.GROQ_USER_MESSAGE.value
        )

        final_messages = ([system_message] if self.generation_system_prompt else []) + messages + [user_message]

        

        response: ChatCompletion = None
        
        try:
            request = dict(
                messages    = final_messages,
                model       = self.generation_model_id,
                stream      = False,
                temperature = temperature if temperature is not None else self.default_temperature,
                max_tokens  = max_output_tokens if max_output_tokens else self.default_max_output_tokens,
            )
            if self.reasoning_effort and self.generation_model_id in {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}:
                request["reasoning_effort"] = self.reasoning_effort
            response = self.client.chat.completions.create(**request)

        except Exception as e:
            if "request" in locals():
                self.logger.error(
                    "Groq request settings | model=%s max_tokens=%s reasoning_effort=%s messages=%s",
                    request["model"], request["max_tokens"],
                    request.get("reasoning_effort", "provider default"), len(request["messages"]),
                )
            log_llm_error(e, provider="groq", model=self.generation_model_id)
            return None
                
        if not self.validate_generation_response(response):
            choice = response.choices[0] if response and response.choices else None
            message = choice.message if choice else None
            usage = getattr(response, "usage", None)
            self.logger.error(
                "Groq empty response | model=%s finish_reason=%s completion_tokens=%s reasoning_tokens=%s reasoning_chars=%s max_tokens=%s",
                self.generation_model_id,
                getattr(choice, "finish_reason", None),
                getattr(usage, "completion_tokens", None),
                getattr(getattr(usage, "completion_tokens_details", None), "reasoning_tokens", None),
                len(getattr(message, "reasoning", None) or ""),
                request["max_tokens"],
            )
            return None
    
        return response.choices[0].message.content


    def validate_generation_response(self, response: ChatCompletion) -> bool:
        return (
            response and
            response.choices and
            len(response.choices) > 0 and
            response.choices[0] and 
            response.choices[0].message and
            response.choices[0].message.content
        )
