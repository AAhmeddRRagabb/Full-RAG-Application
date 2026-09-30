import asyncio
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
        llm_clients           : dict[str, HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient | list[HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient]],
        prompt_template_parser: PromptTemplateParser | None = None,
        tavily_client         : TavilyClient | None = None,
    ):
        super().__init__()

        self.prompt_template_parser = prompt_template_parser
        self.llm_clients = llm_clients
        self.tavily_client = tavily_client


    # ---------------------------------------- Utils ---------------------------------------- #
    def get_tavily_search_results(self, query: str, max_results: int = 5) -> list[dict] | None:
        if self.tavily_client is None:
            self.logger.error("Missing Tavily Client")
            return None

        try:
            response = self.tavily_client.search(
                query = query,
                search_depth = "advanced",
                chunks_per_source = 1,
                max_results = max_results,
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


    def get_resource_name(self, file: str) -> str:
        if "_" not in file:
            return file

        return file.split("_", maxsplit = 1)[1]


    def normalize_llm_json(self, llm_response: str) -> str:
        llm_response = llm_response.strip()

        if llm_response.startswith("```"):
            llm_response = llm_response.strip("`").strip()
            if llm_response.startswith("json"):
                llm_response = llm_response[4:].strip()

        return llm_response


    def get_llm_client(
        self,
        task: str,
        client_idx: int = 0,
    ) -> HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient | None:

        task_clients = self.llm_clients.get(task, None)

        if isinstance(task_clients, list):
            if not task_clients:
                return None

            return task_clients[client_idx % len(task_clients)]

        return task_clients


    async def get_llm_response(
        self,
        task       : str,
        prompt_vars: dict,
        client_idx : int = 0,
    ) -> str | None:
        """
        Args:
            task       : to accomplish [must be from AgentTasks].
            prompt_vars: variables to be injected the task prompt.

        Returns:
            if success -> llm_response
            if failure -> None
        """

        llm_client = self.get_llm_client(
            task = task,
            client_idx = client_idx,
        )

        if llm_client is None:
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

        llm_response = await asyncio.to_thread(
            llm_client.generate_text,
            user_prompt = task_prompt,
        )

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
        Parse LLM Response & Returned Required Key.
        """
        try:
            llm_response: dict = json.loads(
                self.normalize_llm_json(llm_response = llm_response)
            )

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
        client_idx  : int = 0,
    ):
        """
        Call the LLM & parse its response.
        """
        llm_response = await self.get_llm_response(
            task = task,
            prompt_vars = prompt_vars,
            client_idx = client_idx,
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
        client_idx : int = 0,
    ) -> BaseModel | None:
        """
        Call the LLM & validate its response against a schema.
        """
        llm_response = await self.call_llm(
            task = task,
            prompt_vars = prompt_vars,
            client_idx = client_idx,
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


    def parse_action(self, action: NextAction) -> tuple[str, dict]:
        return action.action.lower(), action.arguments


    def get_default_next_action(
        self,
        agent_state    : AgentState,
        files          : list[str],
        search_web     : bool,
        max_file_chunks: int,
        max_web_results: int,
        chat_messages  : list[dict],
    ) -> NextAction:

        if not agent_state.requirements:
            return NextAction(
                reason = "User requirements are missing.",
                action = "understand_user_query",
                arguments = {
                    "query": agent_state.user_query,
                },
            )

        if chat_messages and not agent_state.chat_context:
            return NextAction(
                reason = "Previous chat messages may contain useful context.",
                action = "get_chat_context",
                arguments = {
                    "query": agent_state.user_query,
                    "max_results": 5,
                },
            )

        if (files or search_web) and not agent_state.search_results:
            return NextAction(
                reason = "Still need external evidence to answer.",
                action = "search",
                arguments = {
                    "query": agent_state.user_query,
                    "files": files,
                    "search_web": search_web,
                    "max_file_chunks": max_file_chunks,
                    "max_web_results": max_web_results,
                },
            )

        if not agent_state.final_report:
            return NextAction(
                reason = "Evidence collection is complete.",
                action = "generate_final_report",
                arguments = {
                    "query": agent_state.user_query,
                    "search_results": agent_state.search_results,
                },
            )

        return NextAction(
            reason = "Final report is ready.",
            action = "finish",
            arguments = {},
        )


    async def get_next_action(
        self,
        agent_state    : AgentState,
        files          : list[str],
        search_web     : bool,
        max_file_chunks: int,
        max_web_results: int,
        chat_messages  : list[dict],
    ) -> NextAction:

        default_action = self.get_default_next_action(
            agent_state = agent_state,
            files = files,
            search_web = search_web,
            max_file_chunks = max_file_chunks,
            max_web_results = max_web_results,
            chat_messages = chat_messages,
        )

        next_action = await self.get_next_step(
            query = agent_state.user_query,
            current_state = {
                **agent_state.model_dump(),
                "selected_files": files,
                "search_web": search_web,
                "has_chat_messages": bool(chat_messages),
            },
        )

        try:
            next_action = NextAction.model_validate(next_action)

        except ValidationError as e:
            self.logger.error(f"Error Validating Planner Output: {e}")
            self.logger.error(f"Planner Output: {next_action}")
            return default_action

        action, _ = self.parse_action(next_action)

        if action == "understand_user_query" and agent_state.requirements:
            return default_action

        if action == "get_chat_context" and (not chat_messages or agent_state.chat_context):
            return default_action

        if action == "search" and (agent_state.search_results or (not files and not search_web)):
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


    async def extract_message_evidence(
        self,
        query: str,
        message: dict,
        client_idx: int,
    ) -> list[Evidence]:

        message_content = str(message.get("content") or "").strip()
        if not message_content:
            return []

        message_id = message.get("message_id", "local")

        result: ChatContextRelevanceResult = await self.call_llm_schema(
            task = AgentTasks.CC.value,
            prompt_vars = {
                "query": query,
                "message_content": message_content,
                "message_id": message_id,
                "message_role": message.get("role"),
            },
            schema = ChatContextRelevanceResult,
            client_idx = client_idx,
        )

        if result is None or not result.is_relevant or result.relevance_score is None:
            return []

        return [
            Evidence(
                content = message_content,
                relevance_score = result.relevance_score,
                resource = f"message:{message_id}",
            )
        ]


    async def get_chat_context(
        self,
        query: str,
        chat_messages: list[dict],
        max_results: int = 5,
    ) -> list[Evidence]:

        if not chat_messages:
            return []

        context_groups = await asyncio.gather(*[
            self.extract_message_evidence(
                query = query,
                message = message,
                client_idx = idx,
            )
            for idx, message in enumerate(chat_messages)
        ])

        context = [
            evidence
            for group in context_groups
            for evidence in group
        ]

        return sorted(
            context,
            key = lambda evidence: evidence.relevance_score,
            reverse = True,
        )[:max_results]


    async def extract_file_evidence(
        self,
        query          : str,
        files          : list[str],
        max_file_chunks: int,
        file_searcher  : Callable[[str, str, int], Awaitable[list[RetrievedChunk] | None]] | None,
    ) -> list[Evidence]:

        if not files:
            return []

        if file_searcher is None:
            self.logger.error("File Searcher Not Found")
            return []

        file_evidence: list[Evidence] = []

        for file in files:
            documents = await file_searcher(query, file, max_file_chunks)
            if not documents:
                continue

            result: EvidenceResult = await self.call_llm_schema(
                task = AgentTasks.FI.value,
                prompt_vars = {
                    "query": query,
                    "documents": documents,
                    "resource": self.get_resource_name(file = file),
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
        search_web: bool,
        max_web_results: int,
    ) -> list[Evidence]:

        if not search_web:
            return []

        websearch_results = self.get_tavily_search_results(
            query = query,
            max_results = max_web_results,
        )

        if not websearch_results:
            self.logger.error(f"Error Searching the Web. Search Results: {websearch_results}")
            return []

        result: EvidenceResult = await self.call_llm_schema(
            task = AgentTasks.SI.value,
            prompt_vars = {
                "query": query,
                "websearch_results": websearch_results,
            },
            schema = EvidenceResult,
        )

        if result is None or result.need_additional_info:
            self.logger.error(f"Error Extracting Web Evidence. Search Results: {result}")
            return []

        return result.evidence


    async def search(
        self,
        query          : str,
        files          : list[str],
        file_searcher  : Callable[[str, str, int], Awaitable[list[RetrievedChunk] | None]] | None,
        search_web     : bool,
        max_file_chunks: int = 5,
        max_web_results: int = 5,
    ) -> list[Evidence]:

        evidence: list[Evidence] = []

        file_evidence = await self.extract_file_evidence(
            query = query,
            files = files,
            max_file_chunks = max_file_chunks,
            file_searcher = file_searcher,
        )

        evidence.extend(file_evidence)

        web_evidence = await self.extract_web_evidence(
            query = query,
            search_web = search_web,
            max_web_results = max_web_results,
        )

        evidence.extend(web_evidence)

        return evidence


    async def generate_final_report(
        self,
        agent_state: AgentState,
    ) -> FinalReportResult | None:

        evidence = [
            evidence.model_dump()
            for evidence in [*agent_state.chat_context, *agent_state.search_results]
        ]

        return await self.call_llm_schema(
            task = AgentTasks.RG.value,
            prompt_vars = {
                "query": agent_state.user_query,
                "user_requirements": agent_state.requirements,
                "evidence": evidence,
            },
            schema = FinalReportResult,
        )


    # ---------------------------------------- Final Driver Function ---------------------------------------- #
    async def answer_user_query(
        self,
        query          : str,
        files          : list[str] | None = None,
        retrieve_limit : int = 5,
        search_online  : bool = False,
        file_searcher  : Callable[[str, str, int], Awaitable[list[RetrievedChunk] | None]] | None = None,
        chat_messages  : list[dict] | None = None,
        max_web_results: int = 5,
        max_steps      : int = 8,
    ) -> dict | None:

        files = files or []
        chat_messages = chat_messages or []
        agent_state = AgentState(user_query = query)

        for _ in range(max_steps):
            next_action = await self.get_next_action(
                agent_state = agent_state,
                files = files,
                search_web = search_online,
                max_file_chunks = retrieve_limit,
                max_web_results = max_web_results,
                chat_messages = chat_messages,
            )

            action, arguments = self.parse_action(next_action)

            if action == "finish":
                break

            if action == "understand_user_query":
                agent_state.requirements = await self.understand_user_query(
                    query = arguments.get("query", query),
                )

            elif action == "get_chat_context":
                agent_state.chat_context = await self.get_chat_context(
                    query = arguments.get("query", query),
                    chat_messages = chat_messages,
                    max_results = arguments.get("max_results", 5),
                )

            elif action == "search":
                selected_files = [
                    file
                    for file in arguments.get("files", [])
                    if file in files
                ] or files

                agent_state.search_results = await self.search(
                    query = arguments.get("query", query),
                    files = selected_files,
                    file_searcher = file_searcher,
                    search_web = search_online and bool(arguments.get("search_web", search_online)),
                    max_file_chunks = arguments.get("max_file_chunks", retrieve_limit),
                    max_web_results = arguments.get("max_web_results", max_web_results),
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
