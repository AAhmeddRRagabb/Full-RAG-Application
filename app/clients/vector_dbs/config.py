from enum import Enum
from pydantic import BaseModel
from typing import Literal, Any

# distance methods
class VectorDBDistanceMethods(Enum):
    DOT_DISTANCE = "dot"
    COSINE_SIMILARITY = "cosine_similarity"


class VectorDBProviders(Enum):
    PROVIDER_QDRANT   = "qdrant"
    PROVIDER_PGVEVTOR = "pgvector"

# postgres cfg

class VectorDBPGVectorDistanceMethods(Enum):
    COSINE = 'vector_cosine_ops'
    DOT = 'vector_l2_ops'

class VectorDBPGVectorIndexTypes(Enum):
    HNSW = 'hnsw'
    IVFFLAT = 'ivfflat'


class VectorDBPGVectorTableColumns(Enum):
    ID = 'id'
    TEXT = 'text'
    CHUNK_ID = 'chunk_id'
    VECTOR = 'vector'
    METADATA = 'metadata'
    TABLE_PREFIX = 'pgvector'


# errors
VECTOR_DB_ERROR_INVALID_DATA = -1
VECTOR_DB_ERROR_COLLECTION_NOT_FOUND = -2 
VECTOR_DB_CLIENT_ERROR = -3

class VectorDBResult(BaseModel):
    success: bool
    error_type: Literal[-1, -2, -3] | None = None

    content: Any | None = None  # on success
    error: Any | None = None