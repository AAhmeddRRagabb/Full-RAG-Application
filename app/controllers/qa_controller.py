import asyncio

from clients.llms.config import AgentTasks, PromptTypes
from models.enums import ResponsesEnum
from fastapi import HTTPException


from clients.llms.llm_clients import HuggingfaceLLMClient, GoogleLLMClient, GroqLLMClient
from clients.llms.prompt_templates import PromptTemplateParser
from controllers import VectorDBController
from models.db_models import AssetModel, ChunkModel

from models.db_schemas import User, DataChunk

class QAController:
    def __init__(
        self, 
        llm_client       : HuggingfaceLLMClient | GroqLLMClient | GoogleLLMClient, 
        prompt_parser    : PromptTemplateParser, 
        asset_model      : AssetModel, 
        chunk_model      : ChunkModel, 
        vector_controller: VectorDBController 
    ):
        self.llm_client        = llm_client
        self.prompt_parser     = prompt_parser
        self.asset_model       = asset_model
        self.chunk_model       = chunk_model
        self.vector_controller = vector_controller

    async def answer(self, user: User, query: str, file_ids: list[int], language: str = "en") -> dict:
        assets = await self.asset_model.get_user_assets(user.user_id, "file")

        if assets is None:
            raise HTTPException(500, ResponsesEnum.INTERNAL_SERVER_ERROR.value)
        
        names = {
            asset.asset_id: asset.asset_name
            for asset in assets
            if asset.asset_id in file_ids and asset.asset_name.lower().endswith(".pdf")
        }

        if not names:
            raise HTTPException(400, "Select an uploaded PDF first.")

        chunks = await self.chunk_model.get_user_chunks(user.user_id, list(names))
        if chunks is None:
            raise HTTPException(500, ResponsesEnum.INTERNAL_SERVER_ERROR.value)
        if not chunks:
            return {"answer": "The selected PDF has no searchable content.", "sources": []}

        matches = await self.vector_controller.search_vector_db_collection(
            user_key  = user.user_uuid,
            text      = query,
            limit     = 5,
            chunk_ids = [chunk.chunk_id for chunk in chunks],
        ) or []
        by_id = {chunk.chunk_id: chunk for chunk in chunks}

        # -- get final matches with resources
        excerpts = []
        for match in matches:
            chunk = by_id.get(match.chunk_id)
            if not chunk or not match.text:
                continue

            excerpts.append({
                "content": match.text,
                "source": f"{names[chunk.asset_id]}",
            })

        if not excerpts:
            return {"answer": "I couldn't find relevant information in the selected PDF.", "sources": []}

        # -- answer
        prompt = self.prompt_parser.get_prompt(
            task = AgentTasks.ANSWER.value,
            key  = PromptTypes.TASK_PROMPT.value,
            vars = {"query": query, "excerpts": excerpts},
            language = language,
        )

        if not prompt:
            raise HTTPException(500, ResponsesEnum.INTERNAL_SERVER_ERROR.value)
        
        answer = await asyncio.to_thread(
            self.llm_client.generate_text,
            user_prompt       = prompt,
            max_output_tokens = 1200,
            temperature       = 0.2,
        )

        if not answer:
            raise HTTPException(503, ResponsesEnum.INTERNAL_SERVER_ERROR.value)
        return {
            "answer": answer,
            "sources": list(dict.fromkeys(item["source"] for item in excerpts))[:3],
        }


    # ----------- Comparing ------------------ #
    async def retrieve(self, query: str, user: User, file_id: int, chunks: list[DataChunk]) -> list[str]:
        ids = [chunk.chunk_id for chunk in chunks if chunk.asset_id == file_id]
        if not ids:
            return []
        matches = await self.vector_controller.search_vector_db_collection(
            user_key  = user.user_uuid,
            text      = query,
            limit     = 3,
            chunk_ids = ids,
        ) or []
        
        return [match.text for match in matches if match.text]


    async def compare(self, user: User, query: str, file_ids: list[int], language: str = "en") -> dict:
        if len(file_ids) != 2 or len(set(file_ids)) != 2:
            raise HTTPException(400, "Select two different PDFs.")

        # -- get chunks
        assets = await self.asset_model.get_user_assets(user.user_id, "file")
        if assets is None:
            raise HTTPException(500, ResponsesEnum.INTERNAL_SERVER_ERROR.value)
        names = {
            asset.asset_id: asset.asset_name
            for asset in assets
            if asset.asset_id in file_ids and asset.asset_name.lower().endswith(".pdf")
        }
        if len(names) != 2:
            raise HTTPException(400, "Select two uploaded PDFs.")


        chunks = await self.chunk_model.get_user_chunks(user.user_id, file_ids)
        if chunks is None:
            raise HTTPException(500, ResponsesEnum.INTERNAL_SERVER_ERROR.value)

        # -- retrieving
        results = await asyncio.gather(*(
            self.retrieve(
                query   = query,
                user    = user,
                file_id = file_id,
                chunks  = chunks
            ) for file_id in file_ids)
        )
        if not any(results):
            return {"answer": "I couldn't find relevant information in either PDF.", "sources": []}


        files = [
            {"name": names[file_id], "excerpts": excerpts}
            for file_id, excerpts in zip(file_ids, results)
        ]

        # -- comparing
        prompt = self.prompt_parser.get_prompt(
            task = AgentTasks.COMPARE.value,
            key  = PromptTypes.TASK_PROMPT.value,
            vars = {"query": query, "files": files},
            language = language,
        )

        if not prompt:
            raise HTTPException(500, ResponsesEnum.INTERNAL_SERVER_ERROR.value)
        
        answer = await asyncio.to_thread(
            self.llm_client.generate_text,
            user_prompt       = prompt,
            max_output_tokens = 1500,
            temperature       = 0.2,
        )

        if not answer:
            raise HTTPException(503, ResponsesEnum.INTERNAL_SERVER_ERROR.value)
        return {"answer": answer, "sources": [file["name"] for file in files if file["excerpts"]]}
