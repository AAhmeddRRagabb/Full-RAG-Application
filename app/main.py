# ------------------------------------------------------
# Main Workflow
# ------------------------------------------------------

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app_core.lifespan import lifespan
# from app_core.metrics import setup_metrics
from helpers.config import get_settings


app = FastAPI(lifespan = lifespan)
# setup_metrics(app=app)

BASE_DIR = Path(__file__).resolve().parent
settings = get_settings()
templates = Jinja2Templates(directory = BASE_DIR / "templates")



# routes
from routes.app import auth_router
from routes.app import data_router

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name = "static",
)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         settings.FRONTEND_ORIGIN,
#     ],
#     allow_credentials=True,
#     allow_methods=[
#         "GET",
#         "POST",
#         "PUT",
#         "PATCH",
#         "DELETE",
#         "OPTIONS",
#     ],
#     allow_headers=[
#         "Content-Type",
#         "X-CSRF-Token",
#     ],
# )


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request = request,
        name = "index.html",
        context = {
            "page_title": settings.APP_NAME,
            "app_name"  : "Ahmed Bot",
            "user_name" : "Ahmed",
        },
    )


app.include_router(router = auth_router)
app.include_router(router = data_router)

# app.include_router(router=base_router)
# app.include_router(router = chat_router)