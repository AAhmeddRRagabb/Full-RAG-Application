import json
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ValidationError
from tavily import TavilyClient

from .base_controller import BaseController

from clients.llms.config import AgentTasks, PromptTypes
from clients.llms.llm_clients import (
    GoogleLLMClient,
    GroqLLMClient,
    HuggingfaceLLMClient,
)
from clients.llms.prompt_templates import PromptTemplateParser
from models.system_schemas import RetrievedChunk
from models.system_schemas.agent_schemas import *


class ChatController(BaseController):
    """
    Controller RAG generation workflows.
    """
    
    def __init__(
        self,
        llm_clients           : dict[str, HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient],
        prompt_template_parser: PromptTemplateParser | None = None,
        tavily_client         : TavilyClient | None = None,
    ):
        super().__init__()

        self.prompt_template_parser = prompt_template_parser
        self.llm_clients = llm_clients
        self.tavily_client = tavily_client

    # ---------------------------------------- Utils ---------------------------------------- #
    def get_tavily_search_results(self, query: str) -> list[dict] | None:
        if self.tavily_client is None:
            self.logger.error("Missing Tavily Client")
            return None

        try:
            response = self.tavily_client.search(
                query = query,
                search_depth = "advanced",
                chunks_per_source = 1,
                max_results = 3,
            )
            
        except Exception as e:
            self.logger.error(f"Error Searching for Web Results: {e}")
            return None

        return [
            {
                "content"       : res.get("content"),
                "score"         : res.get("score"),
                "url"           : res.get("url"),
                "published_date": res.get("published_date"),
            }
            for res in response.get("results", [])
        ]


    async def get_llm_response(
        self,
        task       : str,
        prompt_vars: dict,
    ) -> str | None:
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
            key = PromptTypes.TASK_PROMPT.value,
            vars = prompt_vars,
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
            llm_response = llm_response.strip()

            if llm_response.startswith("```"):
                llm_response = llm_response.strip("`").strip()
                if llm_response.startswith("json"):
                    llm_response = llm_response[4:].strip()

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
        response_key: str | None = None,
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
            prompt_vars = prompt_vars,
        )

        if llm_response is None:
            return None

        return self.parse_llm_response(
            llm_response = llm_response,
            key = response_key,
        )

    async def call_llm_schema(
        self,
        task       : str,
        prompt_vars: dict,
        schema     : type[BaseModel],
    ) -> BaseModel | None:
        """
        Call the LLM & validate its response against a schema.
        """
        llm_response = await self.call_llm(
            task = task,
            prompt_vars = prompt_vars,
        )

        if llm_response is None:
            return None

        try:
            return schema.model_validate(llm_response)
        
        except ValidationError as e:
            self.logger.error(f"Error Validating LLM Output: {e}")
            self.logger.error(f"LLM Output: {llm_response}")
            return None


    # ---------------------------------------- Agentic Work ---------------------------------------- #
    async def get_next_step(
        self,
        query: str,
        current_state: dict,
    ):

        return await self.call_llm(
            task = AgentTasks.OR.value,
            prompt_vars = {
                "query": query,
                "state": current_state,
            },
        )


    def _parse_action(self, action: NextAction) -> tuple[str, dict]:
        return action.action.lower(), action.arguments


    def _get_resource_name(self, file: str) -> str:
        if "_" not in file:
            return file

        return file.split("_", maxsplit = 1)[1]


    def get_default_next_action(
        self,
        agent_state   : AgentState,
        files         : list[str],
        retrieve_limit: int,
        search_online : bool,
    ) -> NextAction:

        if not agent_state.requirements:
            return NextAction(
                reason = "User requirements are missing.",
                action = "understand_user_query",
                arguments = {
                    "query": agent_state.user_query,
                },
            )

        if files and not agent_state.retrieved_chunks:
            return NextAction(
                reason = "Selected files still need to be searched.",
                action = "search_files",
                arguments = {
                    "query": agent_state.user_query,
                    "files": files,
                    "retrieve_limit": retrieve_limit,
                },
            )

        if search_online and not agent_state.web_results:
            return NextAction(
                reason = "Online search is enabled and web evidence is missing.",
                action = "search_web",
                arguments = {
                    "query": agent_state.user_query,
                    "max_results": 3,
                },
            )

        if not agent_state.final_report:
            return NextAction(
                reason = "Evidence collection is complete.",
                action = "generate_final_report",
                arguments = {
                    "query": agent_state.user_query,
                },
            )

        return NextAction(
            reason = "Final report is ready.",
            action = "finish",
            arguments = {},
        )


    async def get_planned_next_action(
        self,
        agent_state   : AgentState,
        files         : list[str],
        retrieve_limit: int,
        search_online : bool,
    ) -> NextAction:

        default_action = self.get_default_next_action(
            agent_state = agent_state,
            files = files,
            retrieve_limit = retrieve_limit,
            search_online = search_online,
        )

        next_action = await self.get_next_step(
            query = agent_state.user_query,
            current_state = {
                **agent_state.model_dump(),
                "selected_files": files,
                "search_online": search_online,
            },
        )

        try:
            next_action = NextAction.model_validate(next_action)
        except ValidationError as e:
            self.logger.error(f"Error Validating Planner Output: {e}")
            self.logger.error(f"Planner Output: {next_action}")
            return default_action

        action, _ = self._parse_action(next_action)
        if action == "understand_user_query" and agent_state.requirements:
            return default_action

        if action == "search_files" and not files:
            return default_action

        if action == "search_files" and agent_state.retrieved_chunks:
            return default_action

        if action == "search_web" and not search_online:
            return default_action

        if action == "search_web" and agent_state.web_results:
            return default_action

        if action == "generate_final_report" and agent_state.final_report:
            return default_action

        return next_action

    # ---------------------------------------- Individual LLMs Work ---------------------------------------- #
    async def understand_user_query(self, query: str) -> list[str]:
        result = await self.call_llm_schema(
            task = AgentTasks.QA.value,
            prompt_vars = {
                "query": query,
            },
            schema = QueryUnderstandingResult,
        )

        if result is None:
            return [query]

        return result.requirements or [query]


    async def extract_file_evidence(
        self,
        query         : str,
        files         : list[str],
        retrieve_limit: int,
        file_searcher : Callable[[str, str, int], Awaitable[list[RetrievedChunk] | None]] | None,
    ) -> list[Evidence]:

        if file_searcher is None:
            return []

        file_evidence: list[Evidence] = []

        for file in files:
            documents = await file_searcher(query, file, retrieve_limit)
            if not documents:
                continue

            result = await self.call_llm_schema(
                task = AgentTasks.FI.value,
                prompt_vars = {
                    "query": query,
                    "documents": documents,
                    "resource": self._get_resource_name(file),
                },
                schema = EvidenceResult,
            )

            if result is None or result.need_additional_info:
                continue

            file_evidence.extend(result.evidence)

        return file_evidence


    async def extract_web_evidence(
        self,
        query: str,
        search_online: bool,
    ) -> list[Evidence]:

        if not search_online:
            return []

        websearch_results = self.get_tavily_search_results(query = query)
        if not websearch_results:
            return []

        result = await self.call_llm_schema(
            task = AgentTasks.SI.value,
            prompt_vars = {
                "query": query,
                "websearch_results": websearch_results,
            },
            schema = EvidenceResult,
        )

        if result is None or result.need_additional_info:
            return []

        return result.evidence


    async def generate_final_report(
        self,
        agent_state: AgentState,
    ) -> FinalReportResult | None:

        return await self.call_llm_schema(
            task = AgentTasks.RG.value,
            prompt_vars = {
                "query": agent_state.user_query,
                "user_requirements": agent_state.requirements,
                "file_evidence": [
                    evidence.model_dump()
                    for evidence in agent_state.retrieved_chunks
                ],
                "web_evidence": [
                    evidence.model_dump()
                    for evidence in agent_state.web_results
                ],
            },
            schema = FinalReportResult,
        )

    # ---------------------------------------- Final Driver Function ---------------------------------------- #
    async def answer_user_query(
        self,
        query         : str,
        files         : list[str] | None = None,
        retrieve_limit: int = 5,
        search_online : bool = False,
        file_searcher : Callable[[str, str, int], Awaitable[list[RetrievedChunk] | None]] | None = None,
        max_steps     : int = 8,
    ) -> dict | None:

        # - setup
        files = files or []
        agent_state = AgentState(user_query = query)

        for _ in range(max_steps):
            # - get next action
            next_action = await self.get_planned_next_action(
                agent_state = agent_state,
                files = files,
                retrieve_limit = retrieve_limit,
                search_online = search_online,
            )

            # - execute next action
            action, arguments = self._parse_action(next_action)

            if action == "finish":
                break

            if action == "understand_user_query":
                agent_state.requirements = await self.understand_user_query(
                    query = arguments.get("query", query),
                )

            elif action == "search_files":
                agent_state.retrieved_chunks = await self.extract_file_evidence(
                    query = arguments.get("query", query),
                    files = arguments.get("files") or files,
                    retrieve_limit = arguments.get("retrieve_limit", retrieve_limit),
                    file_searcher = file_searcher,
                )

            elif action == "search_web":
                agent_state.web_results = await self.extract_web_evidence(
                    query = arguments.get("query", query),
                    search_online = search_online,
                )

            elif action == "generate_final_report":
                final_report = await self.generate_final_report(agent_state = agent_state)
                if final_report is None:
                    return None

                agent_state.final_report = final_report.report
                agent_state.llm_resources = final_report.resources

            else:
                self.logger.error(f"Invalid Agent Action: {action}")
                return None

            agent_state.completed_steps.append({
                "action": action,
                "reason": next_action.reason,
            })

        if not agent_state.final_report:
            final_report = await self.generate_final_report(agent_state = agent_state)
            if final_report is None:
                return None

            agent_state.final_report = final_report.report
            agent_state.llm_resources = final_report.resources

        return {
            "report": agent_state.final_report,
            "llm_resources": agent_state.llm_resources,
            "state": agent_state.model_dump(),
        }
