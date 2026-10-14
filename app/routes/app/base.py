from fastapi import APIRouter, Depends
import core.system_settings as CFG


base_router = APIRouter(
    prefix = CFG.APP_ROUTES_ROOT_PATH,
    tags = ["base"]
)

@base_router.get("/health")
async def check_app(
    app_settings: CFG.SystemSettings = Depends(CFG.get_system_settings)
):

    app_name = app_settings.APP_NAME
    app_vers = app_settings.APP_VERSION
    return {
        "APP" : app_name,
        "Version" : app_vers
    }



