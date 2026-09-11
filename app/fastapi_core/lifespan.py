
from fastapi import FastAPI
from contextlib import asynccontextmanager
from helpers.config import get_settings
from helpers.functional import print_title, print_success_message

from helpers.config import get_settings
from clients.llms import LLMAgentFactory
from clients.vector_dbs import VectorDBFactory
from clients.vector_dbs.vector_db_clients import PGVectorVDBClient

from clients.llms.prompt_templates import PromptTemplateParser

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import logging
logger = logging.getLogger('uvicorn')


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    
    print_title("Loading Agents / Clients")

    # connect to PostGres
    print("- Connecting to PostGres:")
    db_url = (
        "postgresql+asyncpg://"
        f"{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}"
        f"/{settings.POSTGRES_MAIN_DB_NAME}"
    )

    app.db_engine = create_async_engine(url = db_url)
    app.db_client = sessionmaker(
        bind   = app.db_engine,
        class_ = AsyncSession,
        expire_on_commit = False
    )

    async with app.db_client() as session:
        await session.execute(text("SELECT 1"))
    print_success_message(f"Connected to: {settings.POSTGRES_MAIN_DB_NAME} Successfully")

    # Vector DB Clients
    print(f"- Connection to Vector DB: {settings.VECTOR_DB_BACKEND}")
    app.vector_db_factory = VectorDBFactory(config = settings, db_client = app.db_client)
    app.vector_db_client = app.vector_db_factory.create_vector_db(provider = settings.VECTOR_DB_BACKEND)
    if not app.vector_db_client:
        logger.error(f"Error While Creating Vector DB Client: {app.vector_db_client}")
        exit()


    if isinstance(app.vector_db_client, PGVectorVDBClient):
        connection = await app.vector_db_client.connect()
        if not connection:
            logger.error(f"Error While Connecting to PGVector: {connection.error}")
            exit()

    print_success_message(f"Connected to: {settings.VECTOR_DB_BACKEND} Successfully")


    # LLM Agents
    llm_agent_factory = LLMAgentFactory(config = settings)
    generation_llm_client = llm_agent_factory.create_agent(provider = settings.GENERATION_BACKEND)
    if not generation_llm_client:
        logger.error(f"Error While Creating Generation Client: {generation_llm_client}")
        exit()

    embedding_llm_client = llm_agent_factory.create_agent(provider = settings.EMBEDDING_BACKEND)
    if not embedding_llm_client:
        logger.error(f"Error While Creating Embedding Client: {embedding_llm_client}")
        exit()


    print_success_message(f"Initiating LLM Agents Successfully")


    app.prompt_template_parser = PromptTemplateParser(
        language = settings.PRIMARY_LANGUAGE,
        default_language = settings.DEFAULT_LANGUAGE
    )
    yield

    await app.db_engine.dispose()
    await app.vector_db_client.disconnect()
    app.generation_client = None
    app.embedding_client = None


    print_title("System Terminated")
