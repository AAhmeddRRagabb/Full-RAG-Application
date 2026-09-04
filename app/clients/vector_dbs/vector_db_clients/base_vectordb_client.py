from abc import ABC, abstractmethod
from typing import Any
from models.system_schemas import RetrievedChunk
from sqlalchemy.ext.asyncio import AsyncSession

import logging

class BaseVectorClient(ABC):
    def __init__(
        self,
        db_path            : str | None = None,
        db_client          : AsyncSession | None = None,
        index_threshold    : int = 100,
        default_vector_size: int = 384,
        distance_method    : str = None,
    ):
        self.db_path             = db_path
        self.db_client           = db_client
        self.index_threshold     = index_threshold
        self.default_vector_size = default_vector_size
        self.distance_method     = distance_method
        self.logger              = logging.getLogger("uvicorn")

    
    # --------------------------- Connection ----------------------------------
    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    # --------------------------- Collections Manipulation ------------------------
    @abstractmethod 
    async def is_collection_existed(self, collection_name: str) -> bool:
        pass
    
    @abstractmethod 
    async def list_all_collections(self) -> list | None:
        pass

    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> dict | None:
        pass

    @abstractmethod
    async def create_collection(
        self,
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False
    ) -> bool:
        pass

    @abstractmethod
    async def delete_collection(
        self,
        collection_name: str
    ) -> bool:
        pass

    # --------------------------- Inserting ----------------------------------
    @abstractmethod
    async def insert_one(
        self,
        collection_name: str,
        record_id: int,
        text: str,
        vector: list[float],
        metadata: dict[str, Any],
    ) -> bool | None:
        pass

    @abstractmethod
    async def insert_many(
        self,
        collection_name: str,
        record_ids: list[int],
        texts: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, Any]],
        batch_size: int = 50
    ) -> bool | None:
        pass


    # search collections
    @abstractmethod
    async def search_by_vector(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5
    ) -> list[RetrievedChunk] | None:
        pass




    
