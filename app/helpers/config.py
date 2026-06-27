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
    MONGODB_URL: str
    MONGODB_DB: str

    # ----------------------------- Secrets ------------------------------- #
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str

    # -------------------------- LLMs Config ----------------------------- #
    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str
    GENERATION_MODEL_ID: str
    EMBEDDING_MODEL_ID: str


    # cfg
    EMBEDDING_SIZE: int
    INPUT_DAFAULT_MAX_CHARACTERS: int
    GENERATION_DAFAULT_MAX_TOKENS: int
    GENERATION_DAFAULT_TEMPERATURE: int

    # -------------------------- Vector DBs Config ----------------------------- #
    VECTOR_DB_BACKEND: str
    VECTOR_DB_NAME: str
    VECTOR_DB_DISTANCE_METHOD: str


    
    class Config:
        env_file = ".env"
    
def get_settings():
    return Settings()