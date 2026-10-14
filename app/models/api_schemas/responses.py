
from pydantic import BaseModel
from .public import UserPublic

# -- auth
class RegisterResponse(BaseModel):
    message: str
    user: UserPublic
    csrf_token: str


class LoginResponse(BaseModel):
    message: str
    user: UserPublic
    csrf_token: str


class CsrfResponse(BaseModel):
    csrf_token: str