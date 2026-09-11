
from fastapi.responses import JSONResponse
from fastapi import status
from models.enums import ResponsesEnum
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

def return_server_error() -> JSONResponse:
    return JSONResponse(
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
        content = {
            "success": False,
            "message": ResponsesEnum.INTERNAL_ERROR.value
        }
    )
