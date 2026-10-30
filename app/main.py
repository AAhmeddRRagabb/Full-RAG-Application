# ------------------------------------------------------
# Main Workflow
# ------------------------------------------------------

from pathlib import Path

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.lifespan import lifespan
from routes.app import auth_router, data_router, qa_router

from core.metrics import setup_metrics

app = FastAPI(lifespan = lifespan)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory = BASE_DIR / "templates")




def render_app(request: Request):
    return templates.TemplateResponse(
        request = request,
        name = "index.html",
        context = {
            "page_title": "Document Q&A",
        },
    )



app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name = "static",
)

setup_metrics(app=app)

@app.get("/")
def home(request: Request):
    return render_app(request = request)


app.include_router(router = auth_router)
app.include_router(router = data_router)
app.include_router(router = qa_router)
