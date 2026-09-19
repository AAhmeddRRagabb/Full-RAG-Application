
from dataclasses import dataclass
from models.db_schemas import User
from models.db_schemas.redis_data import SessionData

@dataclass
class AuthContext:
    user: User
    session_data: SessionData

    session_key: str
    session_hash: str