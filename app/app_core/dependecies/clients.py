

from fastapi import Request

from clients.llms.llm_clients import HuggingfaceLLMClient, GoogleLLMClient, GroqLLMClient
from clients.vector_dbs.vector_db_clients import PGVectorVDBClient
from clients.llms.prompt_templates import PromptTemplateParser

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

def get_redis(request: Request) -> Redis:
    return request.app.state.redis_client

def get_db_client(request: Request) -> AsyncSession:
    return request.app.state.db_client

def get_vector_db_client(request: Request) -> PGVectorVDBClient:
    return request.app.state.vector_db_client

def get_llm_clients(request: Request) -> dict[str, HuggingfaceLLMClient | GoogleLLMClient | GroqLLMClient]:
    return request.app.state.llm_clients

def get_embedding_client(request: Request) -> HuggingfaceLLMClient | GoogleLLMClient:
    return request.app.state.embedding_client

def get_prompt_template_parser(request: Request) -> PromptTemplateParser:
    return request.app.satete.prompt_template_parser