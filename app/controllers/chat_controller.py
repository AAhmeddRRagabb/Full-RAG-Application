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
    QueryUnderstandingResult,
)

from models.db_objects_models import AssetModel, ChunkModel
from .vector_db_controller import VectorDBController

from helpers.chat import ChatCFG, get_file_id
from models.db_schemas import User

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
    def clamp_int(self, value: Any, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = default

        return max(minimum, min(value, maximum))


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

    async def search_file(
        self,
        query: str,
        file_id: int,
        retrieve_limit: int = 5
    ) -> list[RetrievedChunk] | None:

        asset = await self.asset_model.get_user_asset(
            user_id = self.user.user_id, 
            asset_id = file_id
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
        
    
    
    def get_resource_name(self, file: str) -> str:
        if "_" not in file:
            return file

        return file.split("_", maxsplit = 1)[1]




    def get_llm_client(
        self,
        task: str,
    ) -> HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient | None:

        task_clients = self.llm_clients.get(task, None)

        if isinstance(task_clients, list):
            if not task_clients:
                return None

            return task_clients[client_idx % len(task_clients)]

        return task_clients


    async def call_llm_json(
        self,
        task       : str,
        prompt_vars: dict,
        key        : str | None = None,
    ) -> Any | None:
        
        llm_client = self.get_llm_client(
            task = task,
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
        llm_response = await self.call_llm_json(
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
        user_query: str,
        current_state: AgentState,
    ):
        return await self.call_llm_json(
            task = AgentTasks.OR.value,
            prompt_vars = {
                "user_query": user_query,
                "state": current_state.model_dump(),
            },
        )


    def parse_action(self, action: NextAction) -> tuple[str, dict]:
        return action.action.lower(), action.arguments


    async def get_next_action(
        self,
        user_query: str,
        agent_state: AgentState,
    ) -> NextAction | None:

        next_action = await self.get_next_step(
            user_query = user_query,
            current_state = agent_state
        )

        try:
            return NextAction.model_validate(next_action)

        except ValidationError as e:
            self.logger.error(f"Error Validating Planner Output: {e}")
            self.logger.error(f"Planner Output: {next_action}")
            return None



    # ---------------------------------------- Individual LLMs Work ---------------------------------------- #
    async def get_chat_context(
        self,
        user_query: str,
        chat_messages: list[str],
    ) -> tuple[list[str], dict] | None:

        response = await self.call_llm_json(
            task = AgentTasks.CC.value,
            prompt_vars = {
                'user_query': user_query,
                'messages'  : chat_messages
            }
        )

        chat_context = response.get('chat_context')
        references = response.get('references')

        return chat_context, references


    async def extract_file_evidence(
        self,
        query          : str,
        file           : str,
        file_search_limit: int,
    ) -> list[Evidence]:

        print("Came Here.....")
        

        documents = await self.search_file(
            query = query, 
            file_id = get_file_id(file),
            retrieve_limit = file_search_limit
        )

        print(documents)

        return


        if not documents:
            return []

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
            return []

        return result.evidence


    # async def extract_files_evidence(
    #     self,
    #     query            : str,
    #     files            : list[str],
    #     file_search_limit: int,
    # ) -> list[Evidence]:

    #     if not files:
    #         return []


    #     file_results = await asyncio.gather(*[
    #         self.extract_single_file_evidence(
    #             query = query,
    #             file = file,
    #             max_file_chunks = file_search_limit,
    #             file_searcher = file_searcher,
    #         )
    #         for file in files
    #     ])

    #     return [
    #         evidence
    #         for file_evidence in file_results
    #         for evidence in file_evidence
    #     ]


    # async def extract_web_evidence(
    #     self,
    #     query: str,
    #     search_web: bool,
    #     max_web_results: int,
    # ) -> list[Evidence]:

    #     if not search_web:
    #         return []

    #     websearch_results = self.get_tavily_search_results(
    #         query = query,
    #         max_results = max_web_results,
    #     )

    #     if not websearch_results:
    #         self.logger.error(f"Error Searching the Web. Search Results: {websearch_results}")
    #         return []

    #     result: EvidenceResult = await self.call_llm_schema(
    #         task = AgentTasks.SI.value,
    #         prompt_vars = {
    #             "query": query,
    #             "websearch_results": websearch_results,
    #         },
    #         schema = EvidenceResult,
    #     )

    #     if result is None or result.need_additional_info:
    #         self.logger.error(f"Error Extracting Web Evidence. Search Results: {result}")
    #         return []

    #     return result.evidence


    # async def search(
    #     self,
    #     query          : str,
    #     files          : list[str],
    #     file_search_limit: int,
    #     web_search_limit: int,
    # ) -> list[Evidence]:

    #     file_evidence, web_evidence = await asyncio.gather(
    #         self.extract_file_evidence(
    #             query = query,
    #             files = files,
    #             max_file_chunks = max_file_chunks,
    #             file_searcher = file_searcher,
    #         ),
    #         self.extract_web_evidence(
    #             query = query,
    #             search_web = search_web,
    #             max_web_results = max_web_results,
    #         ),
    #     )

    #     return [
    #         *file_evidence,
    #         *web_evidence,
    #     ]


    async def generate_final_report(
        self,
        agent_state: AgentState,
    ) -> FinalReportResult | None:

        evidence = [
            evidence.model_dump()
            for evidence in agent_state.search_results
        ]

        chat_context = [
            context.model_dump()
            for context in agent_state.chat_context
        ]

        return await self.call_llm_schema(
            task = AgentTasks.RG.value,
            prompt_vars = {
                "query": agent_state.enriched_query or agent_state.user_query,
                "user_requirements": agent_state.requirements,
                "chat_context": chat_context,
                "evidence": evidence,
                "answer_mode": agent_state.answer_mode,
                "final_tone": agent_state.final_tone,
            },
            schema = FinalReportResult,
        )


    # ---------------------------------------- Final Driver Function ---------------------------------------- #
    async def answer_user_query(
        self,
        user_query: str,
        chat_cfg : ChatCFG,

        files         : list[str] | None = None,
        chat_messages : list[str] | None = None,

        stage_callback  : Callable[[str], Awaitable[None]] | None = None,
    ) -> dict | None:

        files = files or []
        chat_messages = chat_messages or []
        run_steps: list[dict[str, Any]] = []


        agent_state = AgentState(max_search_limit = chat_cfg.max_search_limit)

        from helpers.functional import print_title
        from pprint import pprint
        while(True):
            print_title(f"Step #{agent_state.total_completed_agentic_steps + 1}")
            
            next_action = await self.get_next_action(
                user_query = user_query,
                agent_state = agent_state,
            )

            action, arguments = self.parse_action(next_action)

            print(f"Next Action:")
            pprint(next_action.model_dump(), indent = 2)
            print()
            

            print("Results:")

            if action == 'get_chat_context':
                chat_context, references = await self.get_chat_context(
                    user_query = user_query,
                    chat_messages = chat_messages,
                )

                agent_state.chat_context = chat_context
                agent_state.references = references

                print("Chat Context:")
                pprint(chat_context)

                print("References:")
                pprint(references)


            elif action == 'search':
                self.extract_file_evidence(
                    query = user_query,
                    file = files[0],
                    file_search_limit = chat_cfg.file_search_limit
                )
    
            else:
                break


        #     step_started = time.perf_counter()
        #     step_input = {
        #         "action": action,
        #         "reason": next_action.reason,
        #         "arguments": arguments,
        #         "state": agent_state.model_dump(),
        #     }
        #     step_output: dict[str, Any] = {}

        #     if stage_callback is not None:
        #         await stage_callback(action)

        #     if action == "finish":
        #         if agent_state.final_report:
        #             run_steps.append({
        #                 "name": action,
        #                 "input": step_input,
        #                 "output": {"finished": True},
        #                 "duration_ms": round((time.perf_counter() - step_started) * 1000, 2),
        #             })
        #             break

        #         continue





        #         if context_item is not None:
        #             agent_state.chat_context.append(context_item)

        #         agent_state.chat_context_reads += 1
        #         agent_state.chat_context_checked = (
        #             bool(agent_state.chat_context)
        #             or agent_state.chat_context_reads >= min(len(chat_messages), 6)
        #         )
     
        #         step_output = {
        #             "chat_context": [
        #                 context.model_dump()
        #                 for context in agent_state.chat_context
        #             ],
        #             "enriched_query": agent_state.enriched_query,
        #             "reads": agent_state.chat_context_reads,
        #             "checked": agent_state.chat_context_checked,
        #         }



        #         agent_state.answer_found = answer_check.answer_found
        #         agent_state.answer_check_reason = answer_check.reason
        #         agent_state.final_report_checked = bool(agent_state.final_report)

        #         if answer_check.suggested_query:
        #             agent_state.enriched_query = answer_check.suggested_query
        #         step_output = answer_check.model_dump()

        #     elif action == "search":
        #         if agent_state.search_attempts >= max_search_steps:
        #             continue

        #         search_results = await self.search(
        #             query = arguments.get("query", agent_state.enriched_query or query),
        #             files = arguments.get("files", []),
        #             file_searcher = file_searcher,
        #             search_web = bool(arguments.get("search_web", False)),
        #             max_file_chunks = arguments.get("max_file_chunks", retrieve_limit),
        #             max_web_results = arguments.get("max_web_results", max_web_results),
        #         )

        #         agent_state.search_results.extend(search_results)
        #         agent_state.search_attempts += 1
        #         agent_state.answer_found = None
        #         agent_state.final_report_checked = False
        #         step_output = {
        #             "search_results": [
        #                 evidence.model_dump()
        #                 for evidence in search_results
        #             ],
        #         }

        #     elif action == "generate_final_report":
        #         agent_state.answer_mode = arguments.get("answer_mode", "grounded")
        #         agent_state.final_tone = arguments.get("final_tone", "technical")

        #         final_report = await self.generate_final_report(agent_state = agent_state)
        #         if final_report is None:
        #             return None

        #         agent_state.final_report = final_report.report
        #         agent_state.llm_resources = final_report.resources
        #         agent_state.answer_found = None
        #         agent_state.final_report_checked = False
        #         step_output = final_report.model_dump()

        #     else:
        #         self.logger.error(f"Invalid Agent Action: {action}")
        #         return None

        #     run_steps.append({
        #         "name": action,
        #         "input": step_input,
        #         "output": step_output,
        #         "duration_ms": round((time.perf_counter() - step_started) * 1000, 2),
        #     })

        #     agent_state.total_completed_steps.append({
        #         "action": action,
        #         "reason": next_action.reason,
        #         "arguments": arguments,
        #     })

        #     if agent_state.final_report and agent_state.final_report_checked and agent_state.answer_found:
        #         break

        # if not agent_state.final_report:
        #     step_started = time.perf_counter()
        #     if stage_callback is not None:
        #         await stage_callback("generate_final_report")

        #     agent_state.answer_mode = "direct" if not agent_state.search_results else "grounded"
        #     final_report = await self.generate_final_report(agent_state = agent_state)
        #     if final_report is None:
        #         return None

        #     agent_state.final_report = final_report.report
        #     agent_state.llm_resources = final_report.resources
        #     run_steps.append({
        #         "name": "generate_final_report",
        #         "input": {
        #             "fallback": True,
        #             "state": agent_state.model_dump(),
        #         },
        #         "output": final_report.model_dump(),
        #         "duration_ms": round((time.perf_counter() - step_started) * 1000, 2),
        #     })

        # return {
        #     "report": agent_state.final_report,
        #     "llm_resources": agent_state.llm_resources,
        #     "state": agent_state.model_dump(),
        #     "steps": run_steps,
        # }
