# ------------------------------------------------------
# Main Workflow
# ------------------------------------------------------

from fastapi import FastAPI
from src.api import base
from dotenv import load_dotenv

load_dotenv()


app = FastAPI()
app.include_router(router = base.base_router)
