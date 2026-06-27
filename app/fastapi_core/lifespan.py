
from fastapi import FastAPI
from pymongo import AsyncMongoClient
from contextlib import asynccontextmanager
from helpers.config import get_settings
from helpers.functional import print_title, print_success_message

from helpers.config import get_settings
from stores.llm_agents import LLMAgentFactory
from stores.vector_dbs import VectorDBFactory

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    
    print_title("Loading Agents / Clients")

    # Mongo DB
    print("- Connecting to MongoDB:")
    app.mongodb_client = AsyncMongoClient(settings.MONGODB_URL)
    app.mongodb = app.mongodb_client[settings.MONGODB_DB]

    await app.mongodb_client.admin.command("ping")
    print_success_message(f"Connected to: {app.mongodb.name} Successfully")

    # Vector DB Clients
    print(f"- Connection to Vector DB: {settings.VECTOR_DB_BACKEND}")
    vector_db_factory = VectorDBFactory(config = settings)
    app.vector_db = vector_db_factory.create_vector_db(provider = settings.VECTOR_DB_BACKEND)
    print_success_message(f"Connected to: {settings.VECTOR_DB_BACKEND} Successfully")



    # LLM Agents
    llm_agent_factory = LLMAgentFactory(config = settings)
    app.generation_agent = llm_agent_factory.create_agent(provider = settings.GENERATION_BACKEND)
    app.embedding_agent = llm_agent_factory.create_agent(provider = settings.EMBEDDING_BACKEND)
    print_success_message(f"Initiating LLM Agents Successfully")


    yield

    await app.mongodb_client.admin.close()
    print("System is being terminated...")
