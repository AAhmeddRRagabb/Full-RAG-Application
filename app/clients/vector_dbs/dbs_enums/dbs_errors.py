from enum import Enum

class VectorDBsErrorsEnum(Enum):
    COLLECTION_ALREADY_EXISTS = "The collection name specified already exists."
    INSERTION_COLLECTION_DOES_NOT_EXIST = "Cannot insert in a non-existing collection."
    SEARCHING_COLLECTION_DOES_NOT_EXIST = "Cannot search in a non-existing collection."
    INSERTION_WHILE_UPLOADING_RECORDS = "Error while inserting records: "
    INSERTION_INVALID_RECORDS = "Invalid records"