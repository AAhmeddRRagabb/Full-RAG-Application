from enum import Enum

class ResponsesEnum(Enum):
    # Files
    FILE_TYPE_NOT_SUPPORTED = "File type not supported."
    FILE_MAX_SIZE_EXCEEDED  = "Max size exceeded."
    FILE_UPLOADING_SUCCESS = "File Uploaded Successfully."
    FILE_UPLOAD_PROCESSING = "File uploaded successfully and is being processed."
    FILE_DELETED_SUCCESSFULLY = "File deleted successfully."
    FILE_NOT_FOUND = "File not found."

    # User
    USER_REGISTERED_SUCCESSFULLY = "User Registered Successfully"
    USER_LOGIN_SUCCESSFULLY = "Login successful"
    USER_LOGGED_OUT_SUCCESSFULLY = "Logged out successfully"
    USER_LOGIN_ERROR = "Invalid email or password"
    USER_FOUND_ALREADY = "This email is reserved for another user"

    # Chat
    CHAT_NOT_FOUND = "Chat not found."
    CHAT_NAME_REQUIRED = "Chat name is required."
    CHAT_DELETED_SUCCESSFULLY = "Chat deleted successfully."

    # Server Error
    INTERNAL_SERVER_ERROR = "An unexpected error occurred. Please try again later."
    RATE_LIMIT_NOT_AVAILABLE = "Service is temporarily unavailable. Please try again later."
    RATE_LIMIT_EXCEEDED = "Too many requests. Please try again later."

    # Auth
    AUTH_NOT_AVAILABLE = "Authentication is temporarily unavailable. Please try again later."
    AUTH_REQUIRED = "Please log in to continue."
    AUTH_INVALID_CRED = "Please log in again."
    AUTH_INVALID_SESSION = "Your session expired. Please log in again."
