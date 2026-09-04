from enum import Enum

# distance methods
class VectorDBDistanceMethods(Enum):
    DOT_DISTANCE = "dot"
    COSINE_SIMILARITY = "cosine_similarity"


class VectorDBProviders(Enum):
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
