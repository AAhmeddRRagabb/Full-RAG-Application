
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from tavily import TavilyClient

from clients.llms import LLMAgentFactory
from clients.llms.config import AgentTasks, PromptTypes
from clients.llms.prompt_templates import PromptTemplateParser
from clients.vector_dbs import VectorDBFactory
from clients.vector_dbs.vector_db_clients import PGVectorVDBClient
from core.system_settings import get_system_settings as get_settings
from core.helpers import print_success_message, print_title


logger = logging.getLogger('uvicorn')


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.settings = get_settings()

    
    print_title("Loading Database Clients")

    # - connect to PostGres
    print("- Connecting to PostGres...")

    app.state.db_engine = create_async_engine(url = app.state.settings.DATABASE_URL)
    app.state.db_client = sessionmaker(
        bind = app.state.db_engine,
        class_ = AsyncSession,
        expire_on_commit = False
    )

    async with app.state.db_client() as session:
        await session.execute(text("SELECT 1"))
    print_success_message(f"Connected to Postgres Successfully")
    print()

    # - connect to vector-db
    print(f"- Connecting to Vector DB: {app.state.settings.VECTOR_DB_BACKEND}...")

    vector_db_factory = VectorDBFactory(config = app.state.settings, db_client = app.state.db_client)
    app.state.vector_db_client = vector_db_factory.create_vector_db(provider = app.state.settings.VECTOR_DB_BACKEND)

    if not app.state.vector_db_client:
        logger.error(f"Error While Creating Vector DB Client: {app.state.vector_db_client}")
        exit()


    if isinstance(app.state.vector_db_client, PGVectorVDBClient):
        if not await app.state.vector_db_client.connect():
            exit()

    print_success_message(f"Connected to: {app.state.settings.VECTOR_DB_BACKEND} Successfully")
    print()



    # - connecting to Redis
    print(f"- Connecting to Redis...")
    app.state.redis_client = Redis.from_url(
        url = app.state.settings.redis_url,
        encoding = "utf-8",
        decode_responses = True
    )

    await app.state.redis_client.ping()
    print_success_message(f"Connected to Redis Successfully")
    print()



    print_title("Loading LLM Clients")

    # LLM Agents

    print(f"- Initiating Prompt Templates Parser...")
    app.state.prompt_template_parser = PromptTemplateParser(
        language = app.state.settings.PRIMARY_LANGUAGE,
        default_language = app.state.settings.DEFAULT_LANGUAGE
    )

    print_success_message(f"Initiated Prompt Template Parser Successfully")
    print()



    print(f"- Initiating LLM Agents...")

    llm_clients_factory = LLMAgentFactory(config = app.state.settings)
    app.state.llm_clients_factory = llm_clients_factory
    app.state.llm_clients = {}

    # -- search agent
    app.state.llm_clients[AgentTasks.SEARCH.value] = llm_clients_factory.create_agent(
        provider = app.state.settings.CHAT_CONTEXT_BACKEND,
        generation_model_id = app.state.settings.CHAT_CONTEXT_AGENT,
        system_prompt       = app.state.prompt_template_parser.get_prompt(
            task = AgentTasks.SEARCH.value,
            key  = PromptTypes.SYSTEM_PROMPT.value
        )
    )

    # -- answer agent
    app.state.llm_clients[AgentTasks.ANSWER.value] = llm_clients_factory.create_agent(
        provider            = app.state.settings.FILES_INFORMATION_EXTRACTION_BACKEND,
        generation_model_id = app.state.settings.FILES_INFORMATION_EXTRACTION_AGENT,
        system_prompt       = app.state.prompt_template_parser.get_prompt(
            task = AgentTasks.ANSWER.value,
            key  = PromptTypes.SYSTEM_PROMPT.value
        )
    )

    # -- orchestration agent
    app.state.llm_clients[AgentTasks.ORCHESTRATION.value] = llm_clients_factory.create_agent(
        provider            = app.state.settings.SEARCH_INFORMATION_EXTRACTION_BACKEND,
        generation_model_id = app.state.settings.SEARCH_INFORMATION_EXTRACTION_AGENT,
        system_prompt       = app.state.prompt_template_parser.get_prompt(
            task = AgentTasks.ORCHESTRATION.value,
            key  = PromptTypes.SYSTEM_PROMPT.value
        )
    )


    if (
        not app.state.llm_clients
        or len(app.state.llm_clients) < 3
        or any(
            client is None
            for client in app.state.llm_clients.values()
        )
    ):
        logger.error(f"Error While Initiating LLMs Agents: {app.state.llm_clients}")
        exit()

    print_success_message(f"Initiated LLM Agents Successfully")
    print()


    print(f"- Initiating Embedding Agent...")
    app.state.embedding_client = llm_clients_factory.create_agent(provider = app.state.settings.EMBEDDING_BACKEND)
    if not app.state.embedding_client:
        logger.error(f"Error While Creating Embedding Client: {app.state.embedding_client}")
        exit()

    print_success_message(f"Initiated Embedding Agent Successfully")
    print()


    print(f"- Connecting to Tavily Client...")
    app.state.tavily_client = TavilyClient(
        api_key = app.state.settings.TAVILY_API_KEY
    )

    if not app.state.tavily_client:
        logger.error(f"Error While Connecting to Tavily Client: {app.state.tavily_client}")
        exit()

    print_success_message(f"Connected to Tavily Client Successfully")
    print()


    print_title("Application starts...")
    print_success_message(f"Reach app at: {app.state.settings.FRONTEND_ORIGIN}")


    yield

    await app.state.db_engine.dispose()
    await app.state.vector_db_client.disconnect()
    await app.state.redis_client.aclose()

    app.state.llm_clients = None
    app.state.llm_clients_factory = None
    app.state.embedding_client = None


    print_title("System Terminated")
