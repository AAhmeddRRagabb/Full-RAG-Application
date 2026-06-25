
from fastapi import FastAPI
from pymongo import AsyncMongoClient
from contextlib import asynccontextmanager
from helpers.config import get_settings
from helpers.functional import print_title


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    
    print_title("Loading Agents / Clients")
    app.mongodb_client = AsyncMongoClient(settings.MONGODB_URL)
    app.mongodb = app.mongodb_client[settings.MONGODB_DB]

    await app.mongodb_client.admin.command("ping")
    print(f">> Connected to: {app.mongodb.name}")

    yield

    await app.mongodb_client.admin.close()
    print("System is being terminated...")
