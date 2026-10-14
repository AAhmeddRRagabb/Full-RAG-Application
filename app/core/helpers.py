from fastapi.responses import JSONResponse
from fastapi import status, HTTPException
from redis.asyncio import Redis, RedisError
from models.enums import ResponsesEnum
from models.api_schemas import ChatPublic, MessagePublic, UserPublic
from models.db_schemas import Chat, Message, User
import logging

logger = logging.getLogger('uvicorn')

RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"



def print_title(title: str) -> None:
    title = f" {title} ".center(100, "=")
    print(title)


def print_error_message(error_message: str) -> None:
    error_message = f" {error_message} ".center(50, "=")
    print(f"{RED}{error_message}{RESET}")


def print_success_message(message: str) -> None:
    print(f"{GREEN}>>>>> {message} <<<<<{RESET}")


def return_bad_request(message: str) -> JSONResponse:
    return JSONResponse(
        status_code = status.HTTP_400_BAD_REQUEST,
        content = {
            "success": False,
            "message": message
        }
    )

def raise_internal_server_error():
    raise HTTPException(
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail = ResponsesEnum.INTERNAL_SERVER_ERROR.value
    )



def log_title(title: str) -> None:
    title = f" {title} ".center(100, "=")
    logger.info(title)




def build_public_user(user: User) -> UserPublic:
    return UserPublic(
        user_name = user.user_name,
        user_email = user.user_email,
        user_uuid_prefix = user.user_uuid.hex[:3],
    )


async def check_rate_limit(redis: Redis, key: str, limit: int, window_seconds: int) -> None:
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)

    except RedisError:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail = ResponsesEnum.RATE_LIMIT_NOT_AVAILABLE.value,
        )

    if count > limit:
        raise HTTPException(
            status_code = status.HTTP_429_TOO_MANY_REQUESTS,
            detail = ResponsesEnum.RATE_LIMIT_EXCEEDED.value,
        )



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

