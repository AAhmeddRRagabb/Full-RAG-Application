# ------------------------------------------------------
# Main Workflow
# ------------------------------------------------------

from fastapi import FastAPI
from routes import base, data
from fastapi_core.lifespan import lifespan


app = FastAPI(lifespan = lifespan)
app.include_router(router = base.base_router)
app.include_router(router = data.data_router)