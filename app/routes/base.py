from fastapi import APIRouter, Depends
import helpers.config as CFG


base_router = APIRouter(
    prefix = CFG.BASE_ROUTES_PREFIX,
    tags = ["base"]
)

@base_router.get("/")
async def welcome(
        app_settings: CFG.Settings = Depends(CFG.get_settings)
    ):

    app_name = app_settings.APP_NAME
    app_vers = app_settings.APP_VERSION
    return {
        "APP" : app_name,
        "Version" : app_vers
    }