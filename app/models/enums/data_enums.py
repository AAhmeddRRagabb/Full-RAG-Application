from enum import Enum

class AssetTypesEnum(Enum):
    ASSET_FILE = "file"


class DatabaseCollectionsEnum(Enum):
    COLLECTION_USERS_NAME = "users"
    COLLECTION_CHUNKS_NAME = "chunks"
    COLLECTION_ASSETS_NAME = "assets"


class FileExtensionsEnum(Enum):
    FILE_TXT = ".txt"
    FILE_PDF = ".pdf"