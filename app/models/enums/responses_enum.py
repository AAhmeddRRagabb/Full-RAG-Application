from enum import Enum

class ResponsesEnum(Enum):
    FILE_TYPE_NOT_SUPPORTED    = "File Type Not Supported"
    FILE_MAX_SIZE_EXCEEDED     = "File Max Size Exceeded"
    FILE_UPLOADING_INNER_ERROR = "File Uploading Error"
    FILE_UPLOADING_SUCCESS     = "File Uploaded Successuflly"
    FILE_PROCESSING_SUCCESS    = "File Processing Succeeded"

    # FILE_PROCESSING_FAILED = "File Processing Failed"
    # PROJECT_FILES_NOT_FOUND = "Project Files Not Found"
    # FILE_INVALID_FILE_NAME = "No File With This Name"


    # Data
    PROJECT_INVALID_ID  = "Invalid Project ID"
    PROJECT_INNER_ERROR = "Error while processing project"
    ASSET_INNER_ERROR   = "Error while processing asset"
    CHUNK_INNER_ERROR   = "Error while processing chunk"



    # vector DB
    VECTOR_DB_INNER_ERROR = "Error while processing"
    VECTOR_DB_COLLECTION_NOT_FOUND = "Collection Not Found"
    VECTOR_DB_INVALID_DATA         = "Invalid Input Data"
    VECTOR_DB_CHUNKS_INSERTION_SUCCESS = "Success"

    # Generation
    GENERATION_ERROR_WHILE_CALLING_AGENT = "An error occured while calling agent, please try again."