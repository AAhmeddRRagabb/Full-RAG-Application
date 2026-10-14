
from dataclasses import dataclass
from models.db_schemas import User
from .session_data import SessionData

@dataclass
class AuthContext:
    user: User
    session_data: SessionData

    session_key: str
    session_hash: str