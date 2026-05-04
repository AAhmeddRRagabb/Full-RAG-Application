# -----------------------------------------
# Contain App Configurations
# -----------------------------------------
from pydantic_settings import BaseSettings

BASE_ROUTES_PREFIX = "/api/v1"
DATA_ROUTES_PREFIX = f"{BASE_ROUTES_PREFIX}/data"

FILE_ALLOWED_TYPES = ['text/plain', 'application/pdf']
FILE_CHUNK_SIZE_B = 512 * 1024
FILE_MAX_SIZE_MB = 10


class Settings(BaseSettings):
    # validate env_var
    APP_NAME: str
    APP_VERSION: str
    
    class Config:
        env_file = ".env"
    
def get_settings():
    return Settings()