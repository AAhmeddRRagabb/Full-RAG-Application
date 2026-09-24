from datetime import datetime

from pydantic import BaseModel, Field


class ANSWER_QUERY_REQUEST(BaseModel):
    query: str
    retrieve_limit: int = 5
    files_to_use: list[str] = Field(default_factory = list)


class ChatSettings(BaseModel):
    search_online       : bool = False
    files               : list[str] | None = None
    tone                : str = "technical"
    model_configurations: dict | None = None


class ChatRequest(BaseModel):
    query: str
    chat_id: int
    retrieve_limit: int = 5
    settings: ChatSettings | None = None


class CreateChatRequest(BaseModel):
    chat_name: str | None = None


class RenameChatRequest(BaseModel):
    chat_name: str


class UpdateChatSettingsRequest(BaseModel):
    settings: ChatSettings


class ChatPublic(BaseModel):
    chat_id: int
    chat_name: str
    settings: ChatSettings = Field(default_factory = ChatSettings)


class MessagePublic(BaseModel):
    message_id: int
    chat_id: int
    role: str
    content: str
    llm_resources: list[str] | None = None
    created_at: datetime | None = None
