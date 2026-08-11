# --------------------------------------- APP CFGs ---------------------------------- #
APP_NAME="Full-RAG-APP"
APP_VERSION="0.1"

# ------------------------------------- LLM Configs ----------------------------------------- #
GENERATION_BACKEND="groq"
EMBEDDING_BACKEND="hugging_face"

# Models
GENERATION_MODEL_ID="llama-3.3-70b-versatile"
EMBEDDING_MODEL_ID="sentence-transformers/all-MiniLM-L6-v2"

# cfg
EMBEDDING_SIZE=384
INPUT_DAFAULT_MAX_CHARACTERS=1024
GENERATION_DAFAULT_MAX_TOKENS=200
GENERATION_DAFAULT_TEMPERATURE=0.1

PRIMARY_LANGUAGE="en"
DEFAULT_LANGUAGE="en"

# ------------------------------------- DBs Config ----------------------------------------- #
VECTOR_DB_BACKEND_LITERAL=["qdrant", "pgvector"]

VECTOR_DB_BACKEND="pgvector"
VECTOR_DB_NAME="pgvector_db"

PGVECTOR_INDEXING_THRESHOLD = 100  # used for building HNSW / ivv clusters
# [if below it  -> will keep it flat --> all data points in the same cluster [very few points -> no need for clustering]]
# [if above it] -> will make clusters for faster searching]

VECTOR_DB_DISTANCE_METHOD="cosine_similarity"



POSTGRES_MAIN_DB_NAME="minirag"


# ------------------------------------- Secrets ----------------------------------------- #
POSTGRES_USERNAME=""
POSTGRES_PASSWORD=""
POSTGRES_HOST=""
POSTGRES_PORT=



GROQ_API_KEY=""
GOOGLE_API_KEY=""
HF_TOKEN=""

OPEN_AI_KEY="asd"
OPEN_AI_URL=""


METRICS_ENDPOINT=""
