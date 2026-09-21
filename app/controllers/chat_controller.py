import json
from typing import Any
from helpers.config import get_settings
from .base_controller import BaseController

from models.enums import ResponsesEnum
from models.db_schemas import DataChunk
from models.system_schemas import RetrievedChunk

# vector db utils
from clients.vector_dbs.vector_db_clients import PGVectorVDBClient


# llms utils
from clients.llms.llm_clients import (
    GoogleLLMClient,
    GroqLLMClient,
    HuggingfaceLLMClient
)

from clients.llms import LLMAgentFactory
from clients.llms.prompt_templates import PromptTemplateParser
from clients.llms.config import LLMsGeneralEmbeddingQueryTypes, LLMsGenerationMessageTypes, LLMsProviders
from fastapi.encoders import jsonable_encoder

from clients.llms.prompt_templates.config import LLMTasks, PromptTypes

class ChatController(BaseController):
    """
    Controller for vector database and RAG generation workflows.
    """
    # -------------------- Setup ------------------------- #
    def __init__(
        self,
        prompt_template_parser: PromptTemplateParser | None = None
    ):
        super().__init__()

        self.llm_factory = LLMAgentFactory(config = get_settings())
        self.prompt_template_parser = prompt_template_parser
        self.llms: dict[str, GroqLLMClient | HuggingfaceLLMClient | GoogleLLMClient] = {}


    def init_llm(self, provider: str, llm_task: str):
        system_prompt = self.prompt_template_parser.get_prompt(
            task = llm_task,
            key = PromptTypes.SYSTEM_PROMPT.value
        )

        self.llms[llm_task] = self.llm_factory.create_agent(
            provider = provider,
            system_prompt = system_prompt
        )


    def get_task_prompt(
        self, 
        task                 : str, 
        documents            : list[RetrievedChunk] | None = None,
        online_search_result : None = None,
        information_resources: list[dict] | None = None
    ):

        if task == LLMTasks.DOCUMENTS_SUMMARIZATION.value:
            vars = {'documents': documents}

        elif task == LLMTasks.ONLINE_SEARCH_SUMMARIZATION.value:
            vars = online_search_result

        elif task == LLMTasks.FINAL_REPORT_GENERATION.value:
            vars = {'information_resources': information_resources}

        return self.prompt_template_parser.get_prompt(
            task = task,
            key = PromptTypes.TASK_PROMPT.value,
            vars = vars
        )


    def get_footer_prompt(self, task: str, query: str | None = None):
        vars = {'query': query}
        return self.prompt_template_parser.get_prompt(
            task = task,
            key = PromptTypes.FOOTER_PROMPT.value,
            vars = vars
        )
    

    async def get_llm_response(
        self, 
        query                : str,
        task                 : str,
        provider             : str = LLMsProviders.HUGGING_FACE.value,
        documents            : list[RetrievedChunk] | None = None,
        online_search_result : None = None,
        information_resources: list[dict] | None = None
    ) -> str:
        """
        Returns:
            if success -> llm_response  
            if failure -> None 
        """
        if not self.llms.get(task, None): self.init_llm(provider = provider, llm_task = task)


        task_prompt = self.get_task_prompt(
            task = task,
            documents = documents,
            online_search_result = online_search_result,
            information_resources = information_resources
        )


        if not task_prompt:
            self.logger.error(f"Error Acquiring Task Prompt. Task Prompt: {task_prompt}")
            return None


        footer_prompt = self.get_footer_prompt(task = task, query = query)
        if not footer_prompt:
            self.logger.error(f"Error Acquiring Footer Prompt. Footer Prompt: {footer_prompt}")
            return None

 
        full_prompt = "\n".join([
            task_prompt,
            footer_prompt,
        ])

        llm_response = self.llms[task].generate_text(user_prompt = full_prompt)

        if not llm_response:
            self.logger.error("Invalid LLM Response")
            return None
    
        return llm_response

        
    def parse_llm_response(
        self,
        llm_response: str,
        key: str
    ) -> Any | None:
        """
        Parse LLM Response & Returned Required Key
        """
        try:
            llm_response: dict = json.loads(llm_response)
        except json.JSONDecodeError:
            self.logger.error(f"Model Returned Invalid JSON: {llm_response}")
            return None

        return llm_response.get(key, None)