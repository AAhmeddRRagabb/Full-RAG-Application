
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime



class UserPublic(BaseModel):
    """User safe-date to return to public"""
    user_name: str
    user_email: EmailStr
    user_uuid_prefix: str

    model_config = ConfigDict(from_attributes = True)


class ChatPublic(BaseModel):
    chat_id: int
    chat_name: str


class MessagePublic(BaseModel):
    message_id: int
    chat_id: int
    role: str
    content: str
    llm_resources: list[str] | None = None
    created_at: datetime | None = None
