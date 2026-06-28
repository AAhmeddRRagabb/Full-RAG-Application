from enum import Enum

class ResponsesEnum(Enum):
    FILE_TYPE_NOT_SUPPORTED = "File Type Not Supported"
    FILE_MAX_SIZE_EXCEEDED = "File Max Size Exceeded"
    FILE_UPLOADED_SUCCESSFULLY = "File Uploaded Successuflly"
    FILE_UPLOADED_FAILED = "File Uploaded Failed"
    FILE_PROCESSING_FAILED = "File Processing Failed"
    FILE_PROCESSING_SUCCEEDED = "File Processing Succeeded"
    PROJECT_FILES_NOT_FOUND = "Project Files Not Found"
    FILE_INVALID_FILE_NAME = "No File With This Name"

    # vector DB
    VECTOR_DB_ERROR_WHILE_INSERTION_CHUNKS = "Error while insertion, please try again later."
    VECTOR_DB_SUCCESS_WHILE_INSERTION_CHUNKS = "Chunks inserted successfully"
    VECTOR_DB_GET_COLLECTION_INFO_FAILED = "An Error Occured while retrieving collection info" 
    VECTOR_DB_GET_RETRIEVAL_FAILED = "An Error Occured while retrieving relevant chunks" 