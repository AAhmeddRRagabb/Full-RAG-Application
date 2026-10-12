import asyncio
import json
import time
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
from models.system_schemas.agent_schemas import (
    AgentState,
    AnswerCheckResult,
    Evidence,
    EvidenceResult,
    FinalReportResult,
    NextAction,
    ReportCompatibilityResult,
)

from models.db_objects_models import AssetModel, ChunkModel
from .vector_db_controller import VectorDBController

from helpers.chat import ChatCFG, get_file_id, emit, get_file_name
from models.db_schemas import User

THINKING_MESSAGE = "Thinking..."
GENERATING_RESPONSE_MESSAGE = "Generating Final Response..."

class ChatController(BaseController):
    """
    Controller RAG generation workflows.
    """

    def __init__(
        self,
        llm_clients           : dict[str, HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient | list[HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient]],
        prompt_template_parser: PromptTemplateParser | None = None,
        tavily_client         : TavilyClient | None = None,
        user                  : User | None = None,
        asset_model: AssetModel | None = None,
        chunk_model: ChunkModel | None = None,
        vector_db_controller: VectorDBController | None = None,
    ):
        super().__init__()

        self.prompt_template_parser = prompt_template_parser
        self.llm_clients = llm_clients
        self.tavily_client = tavily_client
        self.user = user

        self.asset_model = asset_model
        self.chunk_model = chunk_model
        self.vector_db_controller = vector_db_controller

    # ---------------------------------------- Utils ---------------------------------------- #
    def get_tavily_search_results(self, query: str, max_results: int = 5) -> list[dict] | None:
        if self.tavily_client is None:
            self.logger.error("Missing Tavily Client")
            return None

        try:
            response = self.tavily_client.search(
                query = query,
                search_depth = "basic",
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

    async def search_file(self, query: str, file_id: int, retrieve_limit: int = 5) -> list[RetrievedChunk] | None:
        asset = await self.asset_model.get_user_asset(
            user_id = int(self.user.user_id), 
            asset_id = int(file_id)
        )

        if asset is None:
            return None

        chunks = await self.chunk_model.get_user_chunks(
            user_id = self.user.user_id,
            asset_ids = [file_id],
        )

        if chunks is None or not len(chunks):
            return None

        return await self.vector_db_controller.search_vector_db_collection(
            user_key = self.user.user_uuid,
            text = query,
            limit = retrieve_limit,
            chunk_ids = [
                chunk.chunk_id
                for chunk in chunks
            ],
        )
        

    async def call_llm_json( self, task: str, prompt_vars: dict, key: str | None = None) -> Any | None:
        
        llm_client = self.llm_clients.get(task, None)

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

        response = await asyncio.to_thread(
            llm_client.generate_text,
            user_prompt = task_prompt,
        )

        if not response:
            self.logger.error("Invalid LLM Response")
            return None

        try:
            data = json.loads(response)

        except json.JSONDecodeError:
            self.logger.error(f"Model Returned Invalid JSON: {response}")
            return None

        return data if key is None else data.get(key)


    async def call_llm_schema(self, task: str, prompt_vars: dict, schema: type[BaseModel]) -> BaseModel | None:
        """
        Call the LLM & validate its response against a schema.
        """

        llm_response = await self.call_llm_json(
            task = task,
            prompt_vars = prompt_vars
        )

        if llm_response is None:
            return None

        try:
            return schema.model_validate(llm_response)

        except ValidationError as e:
            self.logger.error(f"Error Validating LLM Output: {e}")
            self.logger.error(f"LLM Output: {llm_response}")
            return None


    # ---------------------------------------- Search Utils ---------------------------------------- #
    async def extract_file_evidence(self, query: str, file: str, file_search_limit: int) -> list[Evidence]:
        documents = await self.search_file(
            query = query, 
            file_id = get_file_id(file),
            retrieve_limit = file_search_limit
        )

        if not documents:
            return []

        result: EvidenceResult = await self.call_llm_schema(
            task = AgentTasks.FI.value,
            prompt_vars = {
                "query": query,
                "documents": documents,
                "resource": get_file_name(file = file),
            },
            schema = EvidenceResult,
        )

        if result is None or result.need_additional_info:
            return []

        return result.evidence
    
    async def extract_files_evidence(self, query: str, files: list[str], file_search_limit: int) -> list[Evidence]:
        if not files:
            return []

        file_results = await asyncio.gather(*[
            self.extract_file_evidence(
                query = query,
                file = file,
                file_search_limit = file_search_limit,
            )
            for file in files
        ])

        return [
            evidence
            for file_evidence in file_results
            for evidence in file_evidence
        ]


    async def extract_web_evidence(self, query: str, web_search_limit: int) -> list[Evidence]:
        websearch_results = self.get_tavily_search_results(
            query = query,
            max_results = web_search_limit,
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
    
    # ---------------------------------------- Agentic Work ---------------------------------------- #
    def get_orchestration_state(self, agent_state: AgentState) -> dict[str, Any]:
        return {
            "has_chat_context": agent_state.has_chat_context,
            "references": agent_state.references,
            "has_references": agent_state.has_references,
            "has_search_results": agent_state.has_search_results,
            "max_search_limit": agent_state.max_search_limit,
            "search_attempts": agent_state.search_attempts,
            "answer_found": agent_state.answer_found,
            "answer_reason": agent_state.answer_reason,
            "report_query": agent_state.report_query,
            "has_final_report": agent_state.has_final_report,
            "has_llm_resources": agent_state.has_llm_resources,
            "report_compatible": agent_state.report_compatible,
            "report_tone_probability": agent_state.report_tone_probability,
            "report_check_reason": agent_state.report_check_reason,
        }


    async def get_next_step(self, user_query: str, current_state: dict[str, Any]):
        return await self.call_llm_json(
            task = AgentTasks.OR.value,
            prompt_vars = {
                "user_query": user_query,
                "state"     : current_state,
            }
        )


    def parse_action(self, action: NextAction) -> tuple[str, dict]:
        return action.action.lower(), action.arguments


    async def get_next_action(self, user_query: str, agent_state: AgentState) -> NextAction | None:
        next_action = await self.get_next_step(
            user_query = user_query,
            current_state = self.get_orchestration_state(agent_state)
        )

        try:
            return NextAction.model_validate(next_action)

        except ValidationError as e:
            self.logger.error(f"Error Validating Planner Output: {e}")
            self.logger.error(f"Planner Output: {next_action}")
            return None

    # ---------------------------------------- Individual LLMs Work ---------------------------------------- #
    async def get_chat_context(self, user_query: str, chat_messages: list[str]) -> tuple[list[str], list[dict]]:
        response = await self.call_llm_json(
            task = AgentTasks.CC.value,
            prompt_vars = {
                'user_query': user_query,
                'messages'  : chat_messages
            }
        )

        if response is None:
            return [], []

        chat_context = response.get('chat_context') or []
        references = response.get('references') or []

        return chat_context, references


    async def check_answer(self, user_query: str, agent_state: AgentState) -> AnswerCheckResult | None:
        return await self.call_llm_schema(
            task = AgentTasks.AC.value,
            prompt_vars = {
                "user_query": user_query,
                "chat_context": agent_state.chat_context or [],
                "search_results": [
                    evidence.model_dump()
                    for evidence in agent_state.search_results
                ],
            },
            schema = AnswerCheckResult,
        )

    async def search(
        self,
        query          : str,
        files          : list[str],
        file_search_limit: int,
        web_search_limit: int,
    ) -> list[Evidence]:

        file_evidence, web_evidence = await asyncio.gather(
            self.extract_files_evidence(
                query = query,
                files = files,
                file_search_limit = file_search_limit,
            ),
            self.extract_web_evidence(
                query = query,
                web_search_limit = web_search_limit,
            ),
        )

        return [
            *file_evidence,
            *web_evidence,
        ]


    async def generate_final_report(
        self,
        query: str,
        search_results: list[dict],
        chat_tone: str,
    ) -> FinalReportResult | None:

        return await self.call_llm_schema(
            task = AgentTasks.RG.value,
            prompt_vars = {
                "query": query,
                "user_requirements": [],
                "evidence": search_results or [],
                "answer_mode": "grounded",
                "final_tone": chat_tone,
            },
            schema = FinalReportResult,
        )


    async def check_report_compatability(
        self,
        query: str,
        chat_tone: str,
        report: str,
    ) -> ReportCompatibilityResult | None:

        return await self.call_llm_schema(
            task = AgentTasks.RC.value,
            prompt_vars = {
                "query": query,
                "chat_tone": chat_tone,
                "report": report,
            },
            schema = ReportCompatibilityResult,
        )

    # ---------------------------------------- Final Driver Function ---------------------------------------- #
    async def answer_user_query(
        self,
        user_query: str,
        chat_cfg : ChatCFG,
        queue: asyncio.Queue,

        files         : list[str] | None = None,
        chat_messages : list[str] | None = None,
        run_step_logger: Callable[[dict[str, Any]], Awaitable[None]] | None = None,

    ) -> dict | None:

        files = files or []
        chat_messages = chat_messages or []
        agent_state = AgentState(max_search_limit = chat_cfg.max_search_limit)
        run_steps: list[dict[str, Any]] = []
        orchestration_order = 0

        async def record_step(
            name: str,
            step_input: dict[str, Any] | None,
            step_output: Any,
            started_at: float,
        ) -> None:
            step = {
                "name": name,
                "input": step_input,
                "output": step_output,
                "duration_s": round(time.perf_counter() - started_at, 4),
            }
            run_steps.append(step)
            if run_step_logger is not None:
                await run_step_logger(step)

        await emit(queue = queue, message = THINKING_MESSAGE)
        for _ in range(chat_cfg.max_search_limit + 6):
            orchestration_order += 1
            orchestration_started_at = time.perf_counter()
            orchestration_input = self.get_orchestration_state(agent_state)
            next_action_output = await self.get_next_step(
                user_query = user_query,
                current_state = orchestration_input,
            )

            await record_step(
                name = f"orchestration-{orchestration_order}",
                step_input = orchestration_input,
                step_output = next_action_output,
                started_at = orchestration_started_at,
            )

            if next_action_output is None:
                return None

            try:
                next_action = NextAction.model_validate(next_action_output)

            except ValidationError as e:
                self.logger.error(f"Error Validating Planner Output: {e}")
                self.logger.error(f"Planner Output: {next_action_output}")
                return None

            action, arguments = self.parse_action(next_action)
            if agent_state.final_report and agent_state.report_compatible is None and action == 'generate_final_report':
                action = 'check_report_compatability'
                arguments = {}

            started_at = time.perf_counter()
            step_input: dict[str, Any] | None = None
            step_output: dict[str, Any] | bool | None = None

            try:
                if action == 'get_chat_context':
                    step_input = {"query": user_query}

                    chat_context, references = await self.get_chat_context(
                        user_query = user_query,
                        chat_messages = chat_messages,
                    )

                    agent_state.chat_context = chat_context
                    agent_state.references = references
                    agent_state.has_chat_context = bool(chat_context)
                    agent_state.has_references = bool(references)
                    step_output = {
                        "chat_context": chat_context,
                        "references": references,
                    }
                    
                elif action == 'search':
                    search_query = arguments.get("query") or user_query
                    step_input = {"query": search_query}

                    if agent_state.search_attempts >= agent_state.max_search_limit:
                        await record_step(action, step_input, {"error": "search limit reached"}, started_at)
                        continue

                    search_results = await self.search(
                        query = search_query,
                        file_search_limit = chat_cfg.file_search_limit,
                        files = files,
                        web_search_limit = chat_cfg.web_search_limit,
                    )

                    agent_state.search_results.extend(search_results)
                    agent_state.search_attempts += 1
                    agent_state.has_search_results = bool(agent_state.search_results)
                    step_output = {
                        "search_results": [
                            evidence.model_dump()
                            for evidence in search_results
                        ],
                    }

                elif action == 'check_answer':
                    search_results = [
                        evidence.model_dump()
                        for evidence in agent_state.search_results
                    ]
                    step_input = {
                        "user_query": user_query,
                        "chat_context": agent_state.chat_context,
                        "search_results": search_results,
                    }

                    answer_check = await self.check_answer(
                        user_query = user_query,
                        agent_state = agent_state,
                    )
                    if answer_check is None:
                        await record_step(action, step_input, {"error": "check_answer failed"}, started_at)
                        return None

                    agent_state.answer_found = answer_check.answer_found
                    agent_state.answer_reason = answer_check.reason
                    step_output = answer_check.answer_found

                elif action == 'generate_final_report':
                    search_results = [
                        evidence.model_dump()
                        for evidence in agent_state.search_results
                    ]

                    report_query = arguments.get("query") or user_query

                    step_input = {
                        "query": report_query,
                        "search_results": search_results,
                        "chat_tone": chat_cfg.chat_tone,
                    }

                    await emit(queue = queue, message = GENERATING_RESPONSE_MESSAGE)
                    final_report = await self.generate_final_report(
                        query = report_query,
                        search_results = search_results,
                        chat_tone = chat_cfg.chat_tone,
                    )
                    if final_report is None:
                        await record_step(action, step_input, {"error": "generate_final_report failed"}, started_at)
                        return None

                    agent_state.report_query = report_query
                    agent_state.final_report = final_report.report
                    agent_state.llm_resources = final_report.resources
                    agent_state.has_final_report = bool(agent_state.final_report)
                    agent_state.has_llm_resources = bool(agent_state.llm_resources)
                    agent_state.report_compatible = None
                    agent_state.report_tone_probability = None
                    agent_state.report_check_reason = None
                    step_output = {
                        "report": final_report.report,
                        "resources": final_report.resources,
                    }
                    await record_step(action, step_input, step_output, started_at)
                    action = 'check_report_compatability'
                    arguments = {}
                    started_at = time.perf_counter()

                if action == 'check_report_compatability':
                    if not agent_state.final_report:
                        await record_step(action, None, {"error": "No report to check"}, started_at)
                        return None

                    step_input = {
                        "query": agent_state.report_query or user_query,
                        "chat_tone": chat_cfg.chat_tone,
                        "report": agent_state.final_report,
                    }
                    report_check = await self.check_report_compatability(
                        query = agent_state.report_query or user_query,
                        chat_tone = chat_cfg.chat_tone,
                        report = agent_state.final_report,
                    )
                    if report_check is None:
                        await record_step(action, step_input, {"error": "check_report_compatability failed"}, started_at)
                        return None

                    agent_state.report_compatible = report_check.is_valid and report_check.tone_probability >= 0.5
                    agent_state.report_tone_probability = report_check.tone_probability
                    agent_state.report_check_reason = report_check.reason
                    step_output = {
                        "is_valid": agent_state.report_compatible,
                        "tone_probability": report_check.tone_probability,
                        "reason": report_check.reason,
                    }
                    await record_step(action, step_input, step_output, started_at)

                    if agent_state.report_compatible:
                        finish_started_at = time.perf_counter()
                        await record_step('finish', None, None, finish_started_at)
                        break

                    continue

                if action == 'finish':
                    if not agent_state.report_compatible:
                        await record_step(action, None, {"error": "Report is not compatible yet"}, started_at)
                        continue

                    await record_step(action, None, None, started_at)
                    break

                if action not in {
                    'get_chat_context',
                    'search',
                    'check_answer',
                    'generate_final_report',
                    'check_report_compatability',
                }:
                    await record_step(action, None, {"error": f"Invalid Agent Action: {action}"}, started_at)
                    self.logger.error(f"Invalid Agent Action: {action}")
                    return None

            except Exception as e:
                await record_step(action, step_input, {"error": str(e)}, started_at)
                raise

            await record_step(action, step_input, step_output, started_at)

        if not agent_state.final_report:
            return None

        return {
            "report": agent_state.final_report,
            "llm_resources": agent_state.llm_resources,
            "state": agent_state.model_dump(),
            "steps": run_steps,
        }
