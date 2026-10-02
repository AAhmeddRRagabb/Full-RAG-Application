from datetime import datetime
from typing import Literal
from pydantic import BaseModel



class ChatRequest(BaseModel):
    query: str
    chat_id: int
    tone: Literal[
        "technical",
        "creative"
    ] = "technical"
    depth: Literal[
        "low",
        "moderate",
        "high"
    ] = "moderate"

    files: list[str] | None = None




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
