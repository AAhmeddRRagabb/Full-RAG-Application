from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from core.dependecies.auth import require_csrf
from core.dependecies.clients import (
    get_db_client,
    get_embedding_client,
    get_llm_clients,
    get_prompt_template_parser,
    get_vector_db_client,
)
from core.system_settings import QA_ROUTER_PATH
from clients.llms.config import AgentTasks
from controllers.qa_controller import QAController
from controllers.vector_db_controller import VectorDBController
from models.api_schemas import QuestionRequest
from models.db_models import AssetModel, ChunkModel
from models.db_schemas.redis_data import AuthContext


qa_router = APIRouter(prefix=QA_ROUTER_PATH, tags=["questions"])


@qa_router.post("/ask")
async def ask_question(
    question         : QuestionRequest,
    auth             : Annotated[AuthContext, Depends(require_csrf)],
    db_client        = Depends(get_db_client),
    vector_db_client = Depends(get_vector_db_client),
    embedding_client = Depends(get_embedding_client),
    llm_clients      = Depends(get_llm_clients),
    prompt_parser    = Depends(get_prompt_template_parser),
):
    if not question.query.strip():
        raise HTTPException(400, "Enter a question first.")
    controller = QAController(
        llm_client        = llm_clients[AgentTasks.ANSWER.value],
        prompt_parser     = prompt_parser,
        asset_model       = AssetModel(db_client),
        chunk_model       = ChunkModel(db_client),
        vector_controller = VectorDBController(vector_db_client, embedding_client),
    )
    return await controller.answer(auth.user, question.query.strip(), question.files)


