
from pydantic import BaseModel, EmailStr, ConfigDict
from pydantic import SecretStr

class RegisterRequest(BaseModel):
    user_name: str
    email: EmailStr
    password: SecretStr



class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr


class UserPublic(BaseModel):
    """User safe-date to return to public"""
    user_name: str
    user_email: EmailStr

    model_config = ConfigDict(from_attributes = True)



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