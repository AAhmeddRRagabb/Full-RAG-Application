
from typing import Literal
from pydantic import BaseModel, EmailStr
from pydantic import SecretStr


# -- Auth
class RegisterRequest(BaseModel):
    user_name: str
    email: EmailStr
    password: SecretStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr


# -- chat
class ChatRequest(BaseModel):
    query: str
    chat_id: int
    depth: Literal[
        "low",
        "moderate",
        "high"
    ] = "moderate"

    files: list[str] | None = None


class ChatCFG(BaseModel):
    file_search_limit: int
    web_search_limit: int
    max_search_limit: int
