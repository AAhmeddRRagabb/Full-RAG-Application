

from models.request_schemas.chat import ChatPublic, MessagePublic
from models.db_schemas import Chat, Message



# file: fileId_fileName.ext
def get_file_name(file: str) -> str:
    return file.split("_")[-1].split(".")[0]

def get_file_id(file: str) -> str:
    return file.split("_")[0]



import time
def calc_run_time_s(start_time: float) -> float:
    end_time = time.perf_counter()
    run_time = round((end_time - start_time), 2)

    return run_time


from pydantic import BaseModel
class ChatCFG(BaseModel):
    chat_tone: str
    file_search_limit: int
    web_search_limit: int
    max_search_limit: int
    previous_messages_limit: int = 5

def get_chat_cfg(chat_tone: str, chat_depth: str) -> ChatCFG:
    if chat_depth == 'low':
        return ChatCFG(
            chat_tone = chat_tone,
            file_search_limit = 3,
            web_search_limit = 3,
            max_search_limit = 2,
        )

    if chat_depth == 'moderate':
        return ChatCFG(
            chat_tone = chat_tone,
            file_search_limit = 5,
            web_search_limit = 5,
            max_search_limit = 3,
        )

    if chat_depth == 'high':
        return ChatCFG(
            chat_tone = chat_tone,
            file_search_limit = 8,
            web_search_limit = 8,
            max_search_limit = 5,
        )


# -------- Public for UI -------- #
def build_public_chat(chat: Chat) -> ChatPublic:
    return ChatPublic(
        chat_id   = chat.chat_id,
        chat_name = chat.chat_name,
    )


def build_public_message(message: Message) -> MessagePublic:
    return MessagePublic(
        message_id = message.message_id,
        chat_id = message.chat_id,
        role = message.role,
        content = message.content,
        llm_resources = message.llm_resources,
        created_at = message.created_at,
    )

def get_messages_content(messages: list[Message], chat_context_limit: int = 5) -> list[str] | None:
    sorted_messages = sorted(messages, key = lambda m: m.created_at, reverse = True)

    return [
        m.content
        for m in reversed(sorted_messages[:chat_context_limit])
    ] # get latest => then re-order