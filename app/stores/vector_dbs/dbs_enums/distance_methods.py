from enum import Enum

class DistanceMethodsEnum(Enum):
    DOT_DISTANCE = "dot"
    COSINE_SIMILARITY = "cosine_similarity"

class PGVectorDistanceMethodsEnum(Enum):
    COSINE = 'vector_cosine_ops'
    DOT = 'vector_l2_ops'

class PGVectorIndexTypesEnum(Enum):
    HNSW = 'hnsw'
    IVFFLAT = 'ivfflat'


class PGVectorTableColumnsEnum(Enum):
    ID = 'id'
    TEXT = 'text'
    CHUNK_ID = 'chunk_id'
    VECTOR = 'vector'
    METADATA = 'metadata'
    __TABLE_PREFIX = 'pgvector'