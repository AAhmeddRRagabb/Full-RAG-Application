# ------------------------------------------------------
# Main Workflow
# ------------------------------------------------------

from fastapi import FastAPI
from routes import base
from routes import data_pipeline
from fastapi_core.lifespan import lifespan


app = FastAPI(lifespan = lifespan)
app.include_router(router = base.base_router)
app.include_router(router = data_pipeline.data_pipeline_router)