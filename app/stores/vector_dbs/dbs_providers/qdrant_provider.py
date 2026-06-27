from .vector_db_interface import VectorDBInterface
from dbs_enums import DistanceMethodsEnum, VectorDBsErrorsEnum
from qdrant_client import models, QdrantClient
import logging
from typing import Any

class QDrantProvider(VectorDBInterface):
    def __init__(
        self,
        db_path: str,
        distance_method: str
    ):
        self.db_path = db_path
        
        # distance
        if distance_method == DistanceMethodsEnum.DOT_DISTANCE.value:
            self.distance_method = models.Distance.DOT
        else:
            self.distance_method = models.Distance.COSINE

        self.logger = logging.getLogger(__name__)
        self.client = self.connect()


    # connection
    def connect(self) -> QdrantClient:
        return QdrantClient(
            path = self.db_path
        )
    
    def disconnect(self):
        self.client = None

    # collections info
    def is_collection_existed(self, collection_name: str) -> bool:
        return self.client.collection_exists(collection_name = collection_name)
    
    def list_all_collections(self) -> list[str]:
        return self.client.get_collections()
    
    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        return self.client.get_collection(collection_name = collection_name)
    
    # collections manipulation
    def delete_collection(self, collection_name: str):
        if self.is_collection_existed(collection_name = collection_name):
            self.client.delete_collection(collection_name = collection_name)

    def create_collection(
        self,
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False
    ):
        if do_reset:
            self.delete_collection(collection_name = collection_name)

        
        if self.is_collection_existed(collection_name = collection_name):
            self.logger.error(VectorDBsErrorsEnum.COLLECTION_ALREADY_EXISTS.value)
            return False

        self.client.create_collection(
            collection_name = collection_name,
            vectors_config = models.VectorParams(
                size = embedding_size,
                distance = self.distance_method
            )
        )

        return True



    def insert_one(
        self,
        collection_name: str,
        record_id: int,
        text: str,
        vector: list[float],
        metadata: dict[str, Any],
    ):
        if not self.is_collection_existed(collection_name = collection_name):
            self.logger.error(VectorDBsErrorsEnum.INSERTION_COLLECTION_DOES_NOT_EXIST.value)
            return False
        
        try:
            self.client.upload_points(
                collection_name = collection_name,
                points = [
                    models.Record(
                        vector = vector,
                        payload = {
                            "record_id": record_id,
                            "text": text,
                            "metadata": metadata
                        }
                    )
                ]
            )

        except Exception as e:
            self.logger.error(f"{VectorDBsErrorsEnum.INSERTION_WHILE_UPLOADING_RECORDS.value}{e}")
            return False

        return True
    

    def insert_many(
        self,
        collection_name: str,
        record_ids: list[int],
        texts: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, Any]],
        batch_size: int = 50
    ):
        if not self.is_collection_existed(collection_name = collection_name):
            self.logger.error(VectorDBsErrorsEnum.INSERTION_COLLECTION_DOES_NOT_EXIST.value)
            return False
        
        assert len(record_ids) == len(texts) == len(vectors) == len(metadata), VectorDBsErrorsEnum.INSERTION_INVALID_RECORDS.value

        # insertion
        for i in range(0, len(texts), batch_size):
            batch_ids = record_ids[i : i + batch_size]
            batch_texts = texts[i : i + batch_size]
            batch_vectors = vectors[i : i + batch_size]
            batch_metadata = metadata[i : i + batch_size]


            batch_records = [
                models.Record(
                    vector = batch_vectors[x],
                    payload = {
                        "record_id": batch_ids[x],
                        "text": batch_texts[x],
                        "metadata": batch_metadata[x]
                    }
                )
                for x in range(len(batch_ids))
            ]

            try:
                self.client.upload_points(
                    collection_name = collection_name,
                    points = batch_records
                )
            
            except Exception as e:
                self.logger.error(f"{VectorDBsErrorsEnum.INSERTION_WHILE_UPLOADING_RECORDS.value}{e}")
                return False
        

        return True
    


    # searching
    def search_by_vector(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5
    ):
        if not self.is_collection_existed(collection_name = collection_name):
            self.logger.error(VectorDBsErrorsEnum.SEARCHING_COLLECTION_DOES_NOT_EXIST.value)
            return False
        
        return self.client.query_points(
            collection_name = collection_name,
            query = vector,
            limit = limit
        )



