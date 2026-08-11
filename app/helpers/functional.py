
from fastapi.responses import JSONResponse
from fastapi import status
from models.system_schemas import ComponentResult
import logging

logger = logging.getLogger('uvicorn')

RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"

SUCCESS = 1
FAILURE = 0

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

def parse_component_result(result: ComponentResult, error_message: str | None = None):
    if not result.success:
        if result.error:
            logger.error(f'{error_message}. Error: {result.error}')
        return FAILURE, return_bad_request(result.message)

    return SUCCESS, result.content