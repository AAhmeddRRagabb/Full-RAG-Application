from enum import Enum

class ResponseSignal(Enum):
    FILE_TYPE_NOT_SUPPORTED = "File Type Not Supported"
    FILE_MAX_SIZE_EXCEEDED = "File Max Size Exceeded"
    FILE_UPLOADED_SUCCESSFULLY = "File Uploaded Successuflly"
    FILE_UPLOADED_FAILED = "File Uploaded Failed"
    FILE_PROCESSING_FAILED = "File Processing Failed"
    FILE_PROCESSING_SUCCEEDED = "File Processing Succeeded"