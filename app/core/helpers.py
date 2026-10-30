from fastapi import status, HTTPException
from models.enums import ResponsesEnum
from models.api_schemas import UserPublic
from models.db_schemas import User
import logging
import traceback
from pydantic import ValidationError

logger = logging.getLogger('uvicorn')


def log_llm_error(error: Exception, provider: str, model: str | None = None) -> None:
    frames = traceback.extract_tb(error.__traceback__) if error.__traceback__ else []
    frame = next((item for item in reversed(frames) if "/app/" in item.filename.replace("\\", "/")),
                 frames[-1] if frames else None)
    location = f"{frame.filename}:{frame.lineno}" if frame else "unknown"
    body = getattr(error, "body", None)
    details = body.get("error", body) if isinstance(body, dict) else {}
    details = details if isinstance(details, dict) else {}
    reason = (
        ", ".join(f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in error.errors())
        if isinstance(error, ValidationError) else details.get("message") or str(error)[:300]
    )
    fields = {
        "provider": provider,
        "model": model,
        "type": type(error).__name__,
        "status": getattr(error, "status_code", None),
        "code": details.get("code"),
        "reason": reason,
        "failed_generation": details.get("failed_generation"),
        "location": location,
    }
    lines = "\n".join(f"     {key}: {value}" for key, value in fields.items() if value is not None)
    logger.error("Error: LLM Failure\n   ----------------------\n   Error Details\n%s\n   ----------------------", lines)

GREEN = "\033[92m"
RESET = "\033[0m"



def print_title(title: str) -> None:
    title = f" {title} ".center(100, "=")
    print(title)


def print_success_message(message: str) -> None:
    print(f"{GREEN}>>>>> {message} <<<<<{RESET}")

def raise_internal_server_error():
    raise HTTPException(
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail = ResponsesEnum.INTERNAL_SERVER_ERROR.value
    )



def build_public_user(user: User) -> UserPublic:
    return UserPublic(
        user_name = user.user_name,
        user_email = user.user_email,
        user_uuid_prefix = user.user_uuid.hex[:3],
    )

