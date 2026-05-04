from fastapi import APIRouter
import os
import src.functional.config as CFG

base_router = APIRouter(
    prefix = CFG.MAIN_ROUTES_PREFIX,
    tags = ["base"]
)

@base_router.get("/")
async def welcome():
    app_name = os.getenv("APP_NAME")
    app_vers = os.getenv("APP_VERSION")
    return {
        "APP" : app_name,
        "Version" : app_vers
    }