from enum import Enum

class ResponsesEnum(Enum):
    # Files
    FILE_TYPE_NOT_SUPPORTED = "File type not supported."
    FILE_MAX_SIZE_EXCEEDED  = "Max size exceeded."
    FILE_UPLOADING_SUCCESS = "File Uploaded Successfully."


    # User
    USER_LOGIN_ERROR = "Invalid User Data"
    USER_REGISTERED_SUCCESSFULLY = "User Registered Successfully"
    USER_FOUND_ALREADY = "This email is reserved for another user"

    # Server Error
    INTERNAL_SERVER_ERROR = "An unexpected error occurred. Please try again later."