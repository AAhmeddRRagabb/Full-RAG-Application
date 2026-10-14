# -----------------------------------------
# Contain App Configurations
# -----------------------------------------
from pydantic_settings import BaseSettings
from pydantic import SecretStr


# Routes
APP_ROUTES_ROOT_PATH = "/api/v1"
AUTH_ROUTES_PATH     = f"{APP_ROUTES_ROOT_PATH}/auth"
DATA_ROUTES_PATH     = f"{APP_ROUTES_ROOT_PATH}/data"
CHAT_ROUTER_PATH      = f"{APP_ROUTES_ROOT_PATH}/chat"


# FILE_ALLOWED_TYPES = ['text/plain', 'application/pdf']
FILE_ALLOWED_EXTENSIONS = ['.pdf', '.txt']
FILE_CHUNK_SIZE_B = 512 * 1024
FILE_MAX_SIZE_MB = 10



class SystemSettings(BaseSettings):
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

    TAVILY_API_KEY: str

    DATABASE_URL: str
    # -------------------------- LLMs Config ----------------------------- #
    EMBEDDING_MODEL_ID: str


    # cfg
    EMBEDDING_SIZE: int
    INPUT_DAFAULT_MAX_CHARACTERS: int
    GENERATION_DAFAULT_MAX_TOKENS: int
    GENERATION_DAFAULT_TEMPERATURE: float


    PRIMARY_LANGUAGE: str
    DEFAULT_LANGUAGE: str


    CHAT_CONTEXT_BACKEND: str
    FILES_INFORMATION_EXTRACTION_BACKEND: str
    SEARCH_INFORMATION_EXTRACTION_BACKEND: str
    FINAL_REPORT_GENERATION_BACKEND: str
    ORCHESTRATION_BACKEND: str
    EMBEDDING_BACKEND: str

    CHAT_CONTEXT_AGENT: str
    FILES_INFORMATION_EXTRACTION_AGENT: str
    SEARCH_INFORMATION_EXTRACTION_AGENT: str
    FINAL_REPORT_GENERATION_AGENT: str
    ORCHESTRATION_AGENT: str

    # -------------------------- DBs Config ----------------------------- #
    VECTOR_DB_BACKEND: str
    # VECTOR_DB_NAME: str
    
    PGVECTOR_INDEXING_THRESHOLD: int

    VECTOR_DB_DISTANCE_METHOD: str
    POSTGRES_MAIN_DB_NAME: str

    # -------------------------- Redis Config ----------------------------- #
    redis_url: str = "redis://localhost:6379/0"
    SESSION_ABSOLUTE_DAYS: int = 7
    SESSION_IDLE_MINUTES: int = 60

    CSRF_SECRET: SecretStr  # !
    FRONTEND_ORIGIN: str

    class Config:
        env_file = ".env"


    @property
    def SESSION_COOKIE_NAME(self) -> str: # !
        return "session"
    
def get_system_settings():
    return SystemSettings()
