# ------------------------------------------------------
# Main Workflow
# ------------------------------------------------------

from pathlib import Path

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.lifespan import lifespan
from core.system_settings import get_system_settings as get_settings
from routes.app import auth_router, chat_router, data_router


app = FastAPI(lifespan = lifespan)

BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()
templates = Jinja2Templates(directory = BASE_DIR / "templates")

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name = "static",
)


def render_app(request: Request, page_title: str | None = None):
    return templates.TemplateResponse(
        request = request,
        name = "index.html",
        context = {
            "page_title": page_title or settings.APP_NAME,
            "app_name"  : "Ahmed Bot",
            "user_name" : "Ahmed",
        },
    )


@app.get("/")
def home(request: Request):
    return render_app(request = request)


app.include_router(router = auth_router)
app.include_router(router = data_router)
app.include_router(router = chat_router)


@app.get("/{user_slug}/{chat_slug}")
def chat_page(request: Request, user_slug: str, chat_slug: str):
    return render_app(
        request = request,
        page_title = chat_slug.replace("-", " ").title(),
    )
