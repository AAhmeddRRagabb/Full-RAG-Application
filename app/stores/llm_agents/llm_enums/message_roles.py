from enum import Enum


class GroqMessageRolesEnum(Enum):
    SYSTEM_MESSAGE = "system"
    USER_MESSAGE = "user"
    ASSISTANT_MESSAGE = "assistant"

class GoogleMessageRolesEnum(Enum):
    SYSTEM_MESSAGE = "system"
    USER_MESSAGE = "user"
    ASSISTANT_MESSAGE = "model"