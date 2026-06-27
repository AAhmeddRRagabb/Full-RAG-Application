from abc import ABC, abstractmethod
from typing import Any

class VectorDBInterface(ABC):
    # connection
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    # collections info
    @abstractmethod 
    def is_collection_existed(self, collection_name: str) -> bool:
        pass
    
    @abstractmethod 
    def list_all_collections(self) -> list[str]:
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        pass

    # collections manipulation
    @abstractmethod
    def create_collection(
        self,
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False
    ):
        pass

    @abstractmethod
    def delete_collection(
        self,
        collection_name: str
    ) -> bool:
        pass


    @abstractmethod
    def insert_one(
        self,
        collection_name: str,
        record_id: int,
        text: str,
        vector: list[float],
        metadata: dict[str, Any],
    ):
        pass

    @abstractmethod
    def insert_many(
        self,
        collection_name: str,
        record_ids: list[int],
        texts: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, Any]],
        batch_size: int = 50
    ):
        pass


    # search collections
    @abstractmethod
    def search_by_vector(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5
    ):
        pass




    