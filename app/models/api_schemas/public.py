
from pydantic import BaseModel, EmailStr, ConfigDict



class UserPublic(BaseModel):
    """User safe-date to return to public"""
    user_name: str
    user_email: EmailStr
    user_uuid_prefix: str

    model_config = ConfigDict(from_attributes = True)
