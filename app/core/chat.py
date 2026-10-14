
import time
from asyncio import Queue

from models.db_schemas import Message

from models.api_schemas.requests import ChatCFG


def get_file_name(file: str) -> str:
    return file.split("_")[-1].split(".")[0]

def get_file_id(file: str) -> int:
    return int(file.split("_")[0])

def calc_run_time_s(start_time: float) -> float:
    end_time = time.perf_counter()
    run_time = round((end_time - start_time), 2)
    return run_time



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



def get_messages_content(messages: list[Message], chat_context_limit: int = 5) -> list[str] | None:
    sorted_messages = sorted(messages, key = lambda m: m.created_at, reverse = True)

    return [
        m.content
        for m in reversed(sorted_messages[:chat_context_limit])
    ] # get latest => then re-order


async def emit(queue: Queue, message: str) -> None:
    if message.lower() == 'finish':
        return

    await queue.put({
        "type": "stage",
        "message": message,
    })

