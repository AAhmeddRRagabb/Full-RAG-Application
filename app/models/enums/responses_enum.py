from enum import Enum

class ResponsesEnum(Enum):
    # User Errors
    FILE_TYPE_NOT_SUPPORTED    = "File Type Not Supported"
    FILE_MAX_SIZE_EXCEEDED     = "File Max Size Exceeded"

    # -- user
    USER_INVALID_NAME = "Invalid User Name"
    USER_NOT_FOUND = "User Not Found"

    # -- asset
    ASSET_ALREADY_EXISTS = "Asset has been uploaded already."
    ASSET_INVALID_NAME = "Invalid file name"
    ASSETs_NOT_FOUND = "Files not found. Please, upload files."


    # -- vector-db
    VECTOR_DB_CHUNKS_ALREADY_PUSHED = "Chunks have been already inserted"

    # -- chunks
    CHUNK_USER_HAS_NO_CHUNKS = "No chunks found, please chunk the uploaded asssets first"

    # Success
    FILE_UPLOADING_SUCCESS     = "File Uploaded Successfully"
    FILE_PROCESSING_SUCCESS    = "File Processing Succeeded"

    VECTOR_DB_CHUNKS_INSERTION_SUCCESS = "Chunks Inserted Successfully"



    # vector DB
    # VECTOR_DB_COLLECTION_NOT_FOUND = "Collection Not Found"
    # VECTOR_DB_INVALID_DATA         = "Invalid Input Data"


    # Response for Internel errors
    INTERNAL_ERROR = "An error occured. Please, try again later."