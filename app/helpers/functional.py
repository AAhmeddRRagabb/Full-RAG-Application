
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

