from fastapi import APIRouter, Depends
from fastapi.requests import Request
import helpers.config as CFG


base_router = APIRouter(
    prefix = CFG.APP_ROUTES_ROOT_PATH,
    tags = ["base"]
)

@base_router.get("/health")
async def check_app(
    app_settings: CFG.Settings = Depends(CFG.get_settings)
):

    app_name = app_settings.APP_NAME
    app_vers = app_settings.APP_VERSION
    return {
        "APP" : app_name,
        "Version" : app_vers
    }



