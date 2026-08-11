from enum import Enum

class ResponsesEnum(Enum):
    FILE_TYPE_NOT_SUPPORTED    = "File Type Not Supported"
    FILE_MAX_SIZE_EXCEEDED     = "File Max Size Exceeded"
    FILE_UPLOADING_SUCCESS     = "File Uploaded Successfully"
    FILE_UPLOADING_INNER_ERROR = "File Uploading Error. Please, try again later."

    FILE_PROCESSING_SUCCESS    = "File Processing Succeeded"

    # FILE_PROCESSING_FAILED = "File Processing Failed"
    # USER_FILES_NOT_FOUND = "User Files Not Found"
    # FILE_INVALID_FILE_NAME = "No File With This Name"


    # Data
    USER_INNER_ERROR  = "Error while processing user info. Please, try again."
    USER_INVALID_NAME = "Invalid User Name"
    USER_NOT_FOUND = "User Not Found"

    ASSET_INNER_ERROR = "Error while processing asset. Please, try again."
    ASSET_INVALID_NAME = "Invalid file name"
    ASSET_NOT_FOUND = "Files not found. Please, upload files."
    ASSET_ALREADY_EXISTS = "Asset has been uploaded already."

    CHUNK_INNER_ERROR   = "Error while processing chunk"
    CHUNK_ALREADY_EXISTS = "Asset already chunked for this user"



    # vector DB
    VECTOR_DB_INNER_ERROR = "Error while processing"
    VECTOR_DB_COLLECTION_NOT_FOUND = "Collection Not Found"
    VECTOR_DB_INVALID_DATA         = "Invalid Input Data"
    VECTOR_DB_CHUNKS_INSERTION_SUCCESS = "Success"

    # Generation
    GENERATION_ERROR_WHILE_CALLING_AGENT = "An error occured while calling agent, please try again."
