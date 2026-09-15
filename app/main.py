# ------------------------------------------------------
# Main Workflow
# ------------------------------------------------------
from pathlib import Path
from helpers.config import get_settings

from fastapi.requests import Request
from fastapi import FastAPI
from routes.app import base, data_pipeline, nlp

from fastapi_core.lifespan import lifespan
from fastapi_core.metrics import setup_metrics
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(lifespan = lifespan)
setup_metrics(app = app)

BASE_DIR = Path(__file__).resolve().parent
app.mount(
    "/static",
    StaticFiles(directory = BASE_DIR / "static"),
    name = "static"
)

templates = Jinja2Templates(directory = BASE_DIR / "templates")
settings = get_settings()


@app.get("/")
def home(
    request: Request
):
    return templates.TemplateResponse(
        request = request,
        name = "index.html",
        context = {
            "page_title": settings.APP_NAME,
            "app_name"  : "Ahmed Bot",
            "user_name" : "Ahmed"
        }
    )


app.include_router(router = base.base_router)
app.include_router(router = data_pipeline.data_pipeline_router)
app.include_router(router = nlp.nlp_router)
