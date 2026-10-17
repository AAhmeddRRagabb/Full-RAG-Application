import asyncio
import json
import time
from datetime import datetime
from typing import Any, Awaitable, Callable

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from tavily import TavilyClient

from clients.llms.config import AgentTasks, PromptTypes
from clients.llms.prompt_templates import PromptTemplateParser
from core.chat import ChatCFG, emit, get_file_id
from core.helpers import log_llm_error
from models.agent_models import Evidence, RetrievedChunk
from models.agent_models.schemas import FinalAnswer, QueryAnalysis, SearchQuery
from models.db_models import AssetModel, ChunkModel
from models.db_schemas import Message, User
from models.enums import ResponsesEnum

from .base_controller import BaseController
from .vector_db_controller import VectorDBController


class ChatController(BaseController):
    def __init__(
        self,
        llm_clients: dict,
        prompt_template_parser: PromptTemplateParser | None = None,
        tavily_client: TavilyClient | None = None,
        user: User | None = None,
        asset_model: AssetModel | None = None,
        chunk_model: ChunkModel | None = None,
        vector_db_controller: VectorDBController | None = None,
    ):
        super().__init__()
        self.llm_clients = llm_clients
        self.prompt_template_parser = prompt_template_parser
        self.tavily_client = tavily_client
        self.user = user
        self.asset_model = asset_model
        self.chunk_model = chunk_model
        self.vector_db_controller = vector_db_controller

    async def call_llm(self, task: str, prompt_vars: dict, schema: type[BaseModel], max_output_tokens: int) -> BaseModel:
        client = self.llm_clients[task]
        prompt = self.prompt_template_parser.get_prompt(task=task, key=PromptTypes.TASK_PROMPT.value, vars=prompt_vars)
        if not prompt:
            raise RuntimeError(f"Missing prompt for {task}")

        for _ in range(3):
            response = await asyncio.to_thread(
                client.generate_text,
                user_prompt=prompt,
                max_output_tokens=max_output_tokens,
                temperature=0.4 if task == AgentTasks.ANSWER.value else 0.1,
            )
            if response is None:
                continue
            try:
                return schema.model_validate(json.loads(response))
            except (ValueError, ValidationError) as error:
                log_llm_error(error, provider=type(client).__name__, model=client.generation_model_id)

        raise HTTPException(status_code=503, detail=ResponsesEnum.INTERNAL_SERVER_ERROR.value)

    def get_tavily_search_results(self, query: str, max_results: int) -> list[RetrievedChunk]:
        if self.tavily_client is None:
            raise RuntimeError("Missing Tavily client")
        response = self.tavily_client.search(
            query=query, search_depth="basic", chunks_per_source=1, max_results=max_results,
        )
        return [
            RetrievedChunk(
                text=result.get("content") or "",
                score=result.get("score") or 0.0,
                resource=result.get("url"),
                publish_date=result.get("published_date"),
            )
            for result in response.get("results", [])
        ]

    async def search_file(self, query: str, file_id: int, retrieve_limit: int) -> list[RetrievedChunk]:
        asset = await self.asset_model.get_user_asset(user_id=int(self.user.user_id), asset_id=int(file_id))
        if asset is None:
            return []
        chunks = await self.chunk_model.get_user_chunks(user_id=self.user.user_id, asset_ids=[file_id])
        if not chunks:
            return []
        return await self.vector_db_controller.search_vector_db_collection(
            user_key=self.user.user_uuid,
            text=query,
            limit=retrieve_limit,
            chunk_ids=[chunk.chunk_id for chunk in chunks],
        ) or []

    async def search(self, query: str, files: list[str], chat_cfg: ChatCFG) -> list[Evidence]:
        file_results, web_results = await asyncio.gather(
            asyncio.gather(*[
                self.search_file(query, get_file_id(file), chat_cfg.file_search_limit)
                for file in files
            ]),
            asyncio.to_thread(self.get_tavily_search_results, query, chat_cfg.web_search_limit),
        )
        documents = [
            (chunk, file)
            for file, chunks in zip(files, file_results)
            for chunk in chunks
        ] + [(chunk, chunk.resource) for chunk in web_results]
        return [
            Evidence(
                content=chunk.text,
                relevance_score=max(0.0, min(1.0, chunk.score)),
                resource=str(resource),
            )
            for chunk, resource in documents
            if chunk.text and resource
        ]

    def get_current_date(self) -> str:
        return datetime.now().date().isoformat()

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
            "reason": None,
            "input": step_input,
            "output": step_output,
            "duration_s": round(time.time() - started_at, 4),
        }
        if isinstance(step_output, dict) and "error" in step_output:
            result = "failed"
        elif name == "search":
            result = f"{len(step_output['search_results'])} results"
        elif name == "generate_answer":
            result = f"{len(step_output['answer'])} chars"
        else:
            result = json.dumps(step_output, ensure_ascii=False, default=str)
        self.logger.info("Action: %s | Result: %s", name, result)
        if run_step_logger is not None:
            await run_step_logger(step)

    async def answer_user_query(
        self,
        user_query: str,
        chat_cfg: ChatCFG,
        queue: asyncio.Queue,
        files: list[str] | None = None,
        chat_messages: list[Message] | None = None,
        run_step_logger: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict:
        await emit(queue=queue, message="Thinking...")

        history = [
            {"role": message.role, "content": (message.content or "")[-1000:]}
            for message in (chat_messages or [])[-6:]
        ]
        analysis_input = {"query": user_query, "history": history}
        started_at = time.time()
        try:
            analysis: QueryAnalysis = await self.call_llm(
                AgentTasks.QUERY_ANALYZER.value,
                analysis_input,
                QueryAnalysis,
                1024,
            )
        except Exception as error:
            await self.record_step(
                "query_analyzer",
                {"error": str(error)},
                started_at,
                analysis_input,
                run_step_logger,
            )
            raise
        await self.record_step(
            "query_analyzer",
            analysis.model_dump(),
            started_at,
            analysis_input,
            run_step_logger,
        )

        current_date = None
        if analysis.need_current_info:
            started_at = time.time()
            current_date = self.get_current_date()
            await self.record_step(
                "get_current_date",
                {"current_date": current_date},
                started_at,
                run_step_logger=run_step_logger,
            )

        evidence: list[Evidence] = []
        if analysis.need_search:
            started_at = time.time()
            query_input = {
                "query": analysis.resolved_query,
                "history": history,
                "current_date": current_date,
            }
            try:
                search_query: SearchQuery = await self.call_llm(
                    AgentTasks.SEARCH.value,
                    query_input,
                    SearchQuery,
                    1024,
                )
            except Exception as error:
                await self.record_step(
                    "build_search_query",
                    {"error": str(error)},
                    started_at,
                    query_input,
                    run_step_logger,
                )
                raise
            if current_date and current_date[:4] not in search_query.query:
                search_query.query = f"{search_query.query} {current_date[:4]}"
            await self.record_step(
                "build_search_query",
                search_query.model_dump(),
                started_at,
                query_input,
                run_step_logger,
            )

            started_at = time.time()
            try:
                evidence = await self.search(search_query.query, files or [], chat_cfg)
            except Exception as error:
                await self.record_step(
                    "search",
                    {"error": str(error)},
                    started_at,
                    {"query": search_query.query},
                    run_step_logger,
                )
                raise
            await self.record_step(
                "search",
                {"search_results": [item.model_dump() for item in evidence]},
                started_at,
                {"query": search_query.query},
                run_step_logger,
            )

        await emit(queue=queue, message="Generating Final Response...")
        answer_input = {
            "query": analysis.resolved_query,
            "history": history,
            "search_results": [item.model_dump() for item in evidence],
            "current_date": current_date,
        }
        started_at = time.time()
        try:
            answer: FinalAnswer = await self.call_llm(
                AgentTasks.ANSWER.value,
                {
                    "query": analysis.resolved_query,
                    "history": history,
                    "evidence": evidence,
                    "current_date": current_date,
                },
                FinalAnswer,
                2048,
            )
        except Exception as error:
            await self.record_step(
                "generate_answer",
                {"error": str(error)},
                started_at,
                answer_input,
                run_step_logger,
            )
            raise
        await self.record_step(
            "generate_answer",
            answer.model_dump(),
            started_at,
            answer_input,
            run_step_logger,
        )
        await self.record_step("finish", None, time.time(), run_step_logger=run_step_logger)
        return answer.model_dump()
