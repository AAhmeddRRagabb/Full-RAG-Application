import asyncio
import ast
import json
import operator
import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Literal

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
from models.agent_models import RetrievedChunk
from models.agent_models.schemas import (
    Evidence,
    EvidenceResult,
    FinalAnswer,
    NextAction,

)

from models.db_models import AssetModel, ChunkModel
from models.db_schemas import Message
from .vector_db_controller import VectorDBController

from core.chat import ChatCFG, get_file_id, emit, get_file_name
from models.db_schemas import User
from models.agent_models.tools import WorkflowStep, ToolCall

THINKING_MESSAGE = "Thinking..."
GENERATING_RESPONSE_MESSAGE = "Generating Final Response..."

CALCULATOR_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

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

        self.workflow: list[WorkflowStep] = []

    # ---------------------------------------- Utils ---------------------------------------- #
    def get_tavily_search_results(self, query: str, max_results: int = 5) -> list[RetrievedChunk] | None:
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
            RetrievedChunk(
                text = res.get('content'),
                score = res.get('score'),
                resource = res.get("url"),
                publish_date = res.get("published_date"),
            )

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
        

    async def call_llm_json(
        self, 
        task: str, 
        prompt_vars: dict,
        previous_chat_messages: list[Message] | None = None, 
        key: str | None = None,
        max_output_tokens: int | None = None,
    ) -> Any | None:

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
            messages = previous_chat_messages if task == AgentTasks.ORCHESTRATION.value else None,
            max_output_tokens = max_output_tokens,
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
        self, task: str, prompt_vars: dict, schema: type[BaseModel], max_output_tokens: int | None = None
    ) -> BaseModel | None:
        """
        Call the LLM & validate its response against a schema.
        """
        llm_response = await self.call_llm_json(
            task = task,
            prompt_vars = prompt_vars,
            max_output_tokens = max_output_tokens,
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

        for doc in documents:
            doc.resource = get_file_name(file = file)

        if not documents:
            return []

        result: EvidenceResult = await self.call_llm_schema(
            task = AgentTasks.SEARCH.value,
            prompt_vars = {
                "query": query,
                "documents": documents,
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
            task = AgentTasks.SEARCH.value,
            prompt_vars = {
                "query": query,
                "documents": websearch_results,
            },
            schema = EvidenceResult,
        )

        if result is None or result.need_additional_info:
            return []

        return result.evidence
    
    # ---------------------------------------- Agentic Work ---------------------------------------- #
    def get_current_date(self) -> dict[str, Any]:
        now = datetime.now()
        return now.date().isoformat()


    def calculate(self, expression: str) -> str:
        def eval_node(node):
            if isinstance(node, ast.Expression):
                return eval_node(node.body)

            if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
                return node.value

            if isinstance(node, ast.BinOp) and type(node.op) in CALCULATOR_OPERATORS:
                return CALCULATOR_OPERATORS[type(node.op)](
                    eval_node(node.left),
                    eval_node(node.right),
                )

            if isinstance(node, ast.UnaryOp) and type(node.op) in CALCULATOR_OPERATORS:
                return CALCULATOR_OPERATORS[type(node.op)](eval_node(node.operand))

            raise ValueError("Unsupported arithmetic expression")

        parsed = ast.parse(expression, mode = "eval")
        return str(eval_node(parsed))



    async def get_next_action(self, workflow: list[WorkflowStep]) -> NextAction | None:
        next_action = await self.call_llm_json(
            task = AgentTasks.ORCHESTRATION.value,
            prompt_vars = {
                "workflow": workflow,
            }
        )

        try:
            return NextAction.model_validate(next_action)

        except ValidationError as e:
            self.logger.error(f"Error Validating Planner Output: {e}")
            self.logger.error(f"Planner Output: {next_action}")
            return None

    # ---------------------------------------- Individual LLMs Work ---------------------------------------- #

    async def search(
        self,
        query          : str,
        files          : list[str],
        file_search_limit: int,
        web_search_limit: int,
    ) -> list[Evidence]:

        files_evidence, web_evidence = await asyncio.gather(
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

        evidence = [*files_evidence, *web_evidence]

        return evidence


    async def generate_answer(
        self,
        query: str,
        tone: str,
        search_results: list[Evidence] | None = None,
        query_metadata: dict | None = None
    ) -> FinalAnswer | None:
        return await self.call_llm_schema(
            task = AgentTasks.ANSWER.value,
            prompt_vars = {
                "query": query,
                "tone": tone,
                "evidence": search_results or [],
                **(query_metadata or {})
            },
            schema = FinalAnswer,
            max_output_tokens = 5000,
        )

    # ---------------------------------------- Final Driver Function ---------------------------------------- #
    async def record_step(
        self,
        name: str,
        step_output: Any,
        started_at: float,
        step_input: dict[str, Any] | None = None,
        run_step_logger: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        step = {
            "name": name,
            "input": step_input,
            "output": step_output,
            "duration_s": round(time.time() - started_at, 4),
        }

        self.logger.info(
            "Action: %s\nResult: %s",
            name,
            json.dumps(step_output, ensure_ascii=False, default=str),
        )

        if run_step_logger is not None:
            await run_step_logger(step)


    def update_workflow(self, 
        step_name: Literal['user_query', 'tool_call'], 
        user_query: str | None = None,
        step_details: ToolCall | None = None
    ):
        self.workflow.append(
            WorkflowStep(
                step_name = step_name,
                user_query = user_query,
                step_details = step_details
            )
        )


    async def answer_user_query(
        self,
        user_query: str,
        chat_cfg : ChatCFG,
        queue: asyncio.Queue,

        files         : list[str] | None = None,
        chat_messages : list[Message] | None = None,
        run_step_logger: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict | None:

        files = files or []
        chat_messages = chat_messages or []
        self.workflow = []


        # - metadata
        current_date = None
        calculations: list[dict] = []
        search_results: list[Evidence] = []
        answer: str = None
        resources: dict = {}


        # -------------------- Start ------------------------- #
        await emit(queue = queue, message = THINKING_MESSAGE)
        self.update_workflow('user_query', user_query = user_query)

        while(True):
            next_action = await self.get_next_action(workflow = self.workflow)

            if next_action.action == 'finish':
                await self.record_step(
                    name = next_action.action,
                    started_at = time.time(),
                    step_output = None,
                    run_step_logger = run_step_logger,
                )
                return {
                    'answer': answer,
                    'resources': resources
                }

            if next_action.action == 'get_current_date':
                start_time = time.time()

                current_date = self.get_current_date()
                
                await self.record_step(
                    name = next_action.action,
                    started_at = start_time,
                    step_output = {
                        "current_date": current_date
                    },
                    run_step_logger = run_step_logger
                )

                self.update_workflow('tool_call', step_details = ToolCall(
                    tool_name = next_action.action,
                    tool_reason = next_action.reason,
                    tool_result = f"Current Date: {str(current_date)}"
                ))

                
                
            if next_action.action == 'calculate':
                expression = next_action.arguments.get("expression") or ""
                nl_expression = next_action.arguments.get('natural_language_expression') or ""
                step_input = {"expression": expression}
                start_time = time.time()

                result = self.calculate(expression)
                
                await self.record_step(
                    name = next_action.action,
                    started_at = start_time,
                    step_input = step_input,
                    step_output = {"result": result},
                    run_step_logger = run_step_logger
                )
   

                calculations.append({
                    str(expression): result
                })

                self.update_workflow(step_name = "tool_call", step_details = ToolCall(
                    tool_name = "calculate",
                    tool_reason = next_action.reason,
                    tool_result = f"{str(nl_expression)} Evaluated to: {str(result)}"
                ))


            if next_action.action == "search":
                search_query = next_action.arguments.get("search_query", "query") or user_query
                step_input = {"query": search_query}
                start_time = time.time()

                search_results = await self.search(
                    query = search_query,
                    file_search_limit = chat_cfg.file_search_limit,
                    files = files,
                    web_search_limit = chat_cfg.web_search_limit,
                )


                await self.record_step(
                    name = next_action.action,
                    started_at = start_time,
                    step_input = step_input,
                    step_output = {
                        "search_results": [e.model_dump() for e in search_results]
                    },
                    run_step_logger = run_step_logger
                )

                self.update_workflow(step_name = "tool_call", step_details = ToolCall(
                    tool_name = "search",
                    tool_reason = next_action.reason,
                    tool_result = f"Search tool returned {len(search_results)} information pieces."
                ))


            if next_action.action == "generate_answer":
                generation_query = next_action.arguments.get('generation_query', 'query') or user_query
                step_input = {
                    "query": generation_query,
                    "search_results": [result.model_dump() for result in search_results],
                    "chat_tone": chat_cfg.chat_tone,
                }

                query_metadata = {}

                if current_date: query_metadata['current_date'] = current_date
                if calculations: query_metadata['current_date'] = calculations

                if query_metadata:
                    step_input['query_metadata'] = query_metadata


                await emit(queue = queue, message = GENERATING_RESPONSE_MESSAGE)

                start_time = time.time()
                final = await self.generate_answer(
                    query = generation_query,
                    tone = chat_cfg.chat_tone,
                    search_results = search_results,
                    query_metadata = query_metadata if query_metadata else None
                )

                await self.record_step(
                    name = next_action.action,
                    started_at = start_time,
                    step_input = step_input,
                    step_output = final.model_dump(),
                    run_step_logger = run_step_logger
                )

                self.update_workflow(step_name = "tool_call", step_details = ToolCall(
                    tool_name = 'generate_answer',
                    tool_reason = next_action.reason,
                    tool_result = final.answer
                ))

                answer = final.answer
                resources = final.resources

                

            if next_action.action == 'validate_answer':
                step_input = {"user_query": user_query, "answer": answer}
                start_time = time.time()
                valid = await self.call_llm_json(
                    task = AgentTasks.ANSWER_VALIDATION.value,
                    prompt_vars = step_input,
                    key = "valid",
                )

                await self.record_step(
                    name = next_action.action,
                    started_at = start_time,
                    step_input = step_input,
                    step_output = {"valid": valid},
                    run_step_logger = run_step_logger,
                )

                self.update_workflow(step_name = "tool_call", step_details = ToolCall(
                    tool_name = next_action.action,
                    tool_reason = next_action.reason,
                    tool_result = str(valid),
                ))

            if next_action.action == 'validate_search_results':
                step_input = {
                    "user_query": user_query,
                    "search_results": [result.model_dump() for result in search_results],
                }
                start_time = time.time()
                valid = await self.call_llm_json(
                    task = AgentTasks.SEARCH_RESULTS_VALIDATION.value,
                    prompt_vars = step_input,
                    key = "valid",
                )

                await self.record_step(
                    name = next_action.action,
                    started_at = start_time,
                    step_input = step_input,
                    step_output = {"valid": valid},
                    run_step_logger = run_step_logger,
                )

                self.update_workflow(step_name = "tool_call", step_details = ToolCall(
                    tool_name = next_action.action,
                    tool_reason = next_action.reason,
                    tool_result = str(valid),
                ))


            

