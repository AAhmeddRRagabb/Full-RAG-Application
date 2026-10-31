
from pydantic import BaseModel, EmailStr
from pydantic import SecretStr
from typing import Literal


# -- Auth
class RegisterRequest(BaseModel):
    user_name: str
    email: EmailStr
    password: SecretStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr


# -- question
class QuestionRequest(BaseModel):
    query: str
    files: list[int]
    language: Literal["en", "ar"] = "en"


class CompareRequest(BaseModel):
    query: str
    files: list[int]
    language: Literal["en", "ar"] = "en"
