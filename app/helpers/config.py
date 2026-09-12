# -----------------------------------------
# Contain App Configurations
# -----------------------------------------
from pydantic_settings import BaseSettings
from typing import List, Literal

BASE_ROUTES_PREFIX = "/api/v1"
DATA_ROUTES_PREFIX = f"{BASE_ROUTES_PREFIX}/data"
NLP_ROUTES_PREFIX = f"{BASE_ROUTES_PREFIX}/nlp"


# FILE_ALLOWED_TYPES = ['text/plain', 'application/pdf']
FILE_ALLOWED_EXTENSIONS = ['.pdf', '.txt']
FILE_CHUNK_SIZE_B = 512 * 1024
FILE_MAX_SIZE_MB = 10


class Settings(BaseSettings):
    # ----------------------------- APP CGs ------------------------------- #
    APP_NAME: str
    APP_VERSION: str
    
    

    # ----------------------------- Secrets ------------------------------- #
    GROQ_API_KEY: str
    GOOGLE_API_KEY: str
    HF_TOKEN: str
    OPEN_AI_KEY: str
    OPEN_AI_URL: str | None = None

    # postgres
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    METRICS_ENDPOINT: str

    # -------------------------- LLMs Config ----------------------------- #
    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str
    GENERATION_MODEL_ID: str
    EMBEDDING_MODEL_ID: str


    # cfg
    EMBEDDING_SIZE: int
    INPUT_DAFAULT_MAX_CHARACTERS: int
    GENERATION_DAFAULT_MAX_TOKENS: int
    GENERATION_DAFAULT_TEMPERATURE: float


    PRIMARY_LANGUAGE: str
    DEFAULT_LANGUAGE: str

    # -------------------------- DBs Config ----------------------------- #
    VECTOR_DB_BACKEND_LITERAL: List[Literal["qdrant", "pgvector", "milvus"]]

    VECTOR_DB_BACKEND: str
    # VECTOR_DB_NAME: str
    
    PGVECTOR_INDEXING_THRESHOLD: int

    VECTOR_DB_DISTANCE_METHOD: str
    POSTGRES_MAIN_DB_NAME: str


    
    class Config:
        env_file = ".env"
    
def get_settings():
    return Settings()
