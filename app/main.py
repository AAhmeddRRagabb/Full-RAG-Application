# ------------------------------------------------------
# Main Workflow
# ------------------------------------------------------

from fastapi import FastAPI
from routes import base, data
from pymongo import AsyncMongoClient
from contextlib import asynccontextmanager
from helpers.config import get_settings



@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.mongodb_client = AsyncMongoClient(settings.MONGODB_URL)
    app.mongodb = app.mongodb_client[settings.MONGODB_DB]

    await app.mongodb_client.admin.command("ping")
    print(100 * '=')
    print(f"Connected to: {app.mongodb.name}")
    print(100 * '=')

    yield

    await app.mongodb_client.admin.close()
    print(100 * '=')
    print("MongoDB Connection Close")
    print(100 * '=')


app = FastAPI(lifespan = lifespan)
app.include_router(router = base.base_router)
app.include_router(router = data.data_router)