import json
from typing import Any
from .base_controller import BaseController



# llms utils
from clients.llms.llm_clients import (
    GoogleLLMClient,
    GroqLLMClient,
    HuggingfaceLLMClient
)
from tavily import TavilyClient

from clients.llms import LLMAgentFactory
from clients.llms.prompt_templates import PromptTemplateParser
from clients.llms.config import LLMsGeneralEmbeddingQueryTypes, LLMsGenerationMessageTypes, LLMsProviders
from fastapi.encoders import jsonable_encoder

from clients.llms.config import AgentTasks, PromptTypes

class ChatController(BaseController):
    """
    Controller for vector database and RAG generation workflows.
    """
    # -------------------- Setup ------------------------- #
    def __init__(
        self,
        llm_clients           : dict[str, HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient],
        prompt_template_parser: PromptTemplateParser | None = None,
        tavily_client         : TavilyClient | None = None
    ):
        super().__init__()


        self.prompt_template_parser = prompt_template_parser
        self.llm_clients = llm_clients
        self.tavily_client = tavily_client


    def get_tavily_search_results(self, query: str) -> dict | None:
        try:
            response = self.tavily_client.search(
                query = query,
                search_depth = 'advanced',  # ['advanced', 'basic', 'fast', 'ultra-fast']
                chunks_per_source = 1,       # max num of relevant chunks per source
                max_results = 3 
            )
        except Exception as e:
            self.logger.error(f"Error Searching for Web Results: {e}")
            return None

        return [
            {
                'content'       : res.get('content'),
                'score'         : res.get('score'),
                'url'           : res.get('url'),
                'published_date': res.get('published_date')
            }
            for res in response['results']
        ]


    async def get_llm_response(
        self, 
        task       : str,
        prompt_vars: dict
    ) -> str:
        """
        Args:
            task       : to accomplish [must be from AgentTasks].
            prompt_vars: variables to be injected the task prompt.

        Returns:
            if success -> llm_response  
            if failure -> None 
        """

        if not self.llm_clients.get(task, None):
            self.logger.error(f"Missing LLM Client for Task: {task}")
            return None

        task_prompt = self.prompt_template_parser.get_prompt(
            task = task,
            key  = PromptTypes.TASK_PROMPT.value,
            vars = prompt_vars
        )

        if not task_prompt:
            self.logger.error(f"Error Acquiring Task Prompt. Task Prompt: {task_prompt}")
            return None


        llm_response = self.llm_clients[task].generate_text(user_prompt = task_prompt)
        if not llm_response:
            self.logger.error("Invalid LLM Response")
            return None
    
        return llm_response

        
    def parse_llm_response(
        self,
        llm_response: str,
        key: str | None = None,
    ) -> Any | None:
        """
        Parse LLM Response & Returned Required Key
        """
        try:
            llm_response: dict = json.loads(llm_response)
        except json.JSONDecodeError:
            self.logger.error(f"Model Returned Invalid JSON: {llm_response}")
            return None

        if not key:
            return llm_response

        return llm_response.get(key, None)


    async def call_llm(
        self,
        task        : str,
        prompt_vars : dict,
        response_key: str | None = None
    ):
        """
        Call the LLM & parse its response.

        Args:
            task        : to accomplish [must be from AgentTasks].
            prompt_vars : variables to be injected the task prompt.
            response_key: if specified => return only that specific value from the LLM response 

        Return:
            on success => the LLM response or the specified key
            on failure => None
        """
        llm_response = await self.get_llm_response(
            task = task,
            prompt_vars = prompt_vars
        )


        return self.parse_llm_response(
            llm_response = llm_response,
            key = response_key
        )
