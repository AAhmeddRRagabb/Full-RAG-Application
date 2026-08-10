


from .base_vectordb_client import BaseVectorClient

from clients.vector_dbs.config import (
    VectorDBDistanceMethods,

    VECTOR_DB_ERROR_COLLECTION_NOT_FOUND,
    VECTOR_DB_ERROR_INVALID_DATA,
    VECTOR_DB_CLIENT_ERROR,
    VectorDBResult
)

from qdrant_client import models, QdrantClient
import logging
from typing import Any
from models.db_schemas import RetrievedChunk

class QDrantVDBClient(BaseVectorClient):
    def __init__(
        self,
        db_path: str,
        default_vector_size: int = 384,
        distance_method: str = None,
    ):
        super().__init__(
            db_path             = db_path,
            distance_method     = distance_method,
            default_vector_size = default_vector_size
        )
        
        # distance
        if self.distance_method == VectorDBDistanceMethods.DOT_DISTANCE.value:
            self.distance_method = models.Distance.DOT
        else:
            self.distance_method = models.Distance.COSINE

        self.logger = logging.getLogger('uvicorn')
        self.client: QdrantClient = self.connect()


    # connection
    async def connect(self) -> QdrantClient:
        try:
            return QdrantClient(
                path = self.db_path
            )
        except Exception as e:
            return self._return_failure(error_type = VECTOR_DB_CLIENT_ERROR, error = e)
        
    
    async def disconnect(self):
        self.client = None

    # collections info
    async def is_collection_existed(self, collection_name: str) -> VectorDBResult:
        """
        Check if the given collection name exists or not

        Returns:
            VectorDBResult
                - if success -> bool content whether the collection exists or not
                - if failure -> error & error type
        """
        try:
            is_existed = self.client.collection_exists(collection_name = collection_name)
        except Exception as e:
            return self._return_failure(error_type = VECTOR_DB_CLIENT_ERROR, error = e)

        return self._return_success(is_existed)


    
    async def list_all_collections(self) -> VectorDBResult:
        """
        List the collections exist in the database

        Returns:
            VectorDBResult
                - if success -> list of collection name
                - if failure -> error & error type
        """
        try:
            collections = self.client.get_collections()
        except Exception as e:
            return self._return_failure(error_type = VECTOR_DB_CLIENT_ERROR, error = e)

        return self._return_success(collections)


    
    async def get_collection_info(self, collection_name: str) -> VectorDBResult:
        """
        Get info about the given collection name

        Returns:
            VectorDBResult
                - if success -> dict contains the collection info
                - if failure -> error & error type
        """

        # check for existance
        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed.success or not is_collection_existed.content:
            return self._return_failure(error_type = VECTOR_DB_ERROR_COLLECTION_NOT_FOUND) 

        try: 
            info = self.client.get_collection(collection_name = collection_name)
        except Exception as e:
            return self._return_failure(error_type = VECTOR_DB_CLIENT_ERROR, error = e)

        return self._return_success(info)


    
    # collections manipulation
    async def delete_collection(self, collection_name: str) -> VectorDBResult:
        """
        Delete the given collection

        Returns:
            VectorDBResult
                - if success -> None
                - if failure -> error & error type
        """
        is_collection_existed = await self.is_collection_existed(collection_name)
        if is_collection_existed.success and is_collection_existed.content:
            try:
                self.client.delete_collection(collection_name = collection_name)
            except Exception as e:
                return self._return_failure(error_type = VECTOR_DB_CLIENT_ERROR, error = e)

        return self._return_success()


    
    async def create_collection(self, collection_name, embedding_size: int | None = None, do_reset = False) -> VectorDBResult:
        """
        Create a collection with the given name

        Returns:
            VectorDBResult
                - if success -> None
                - if failure -> error & error type
        """
        embedding_size = embedding_size if embedding_size else self.default_vector_size

        if do_reset:
            _ = await self.delete_collection(collection_name = collection_name)

        
        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed.content:
            self.logger.info(f"Creating Collection: {collection_name}")

            try:
                self.client.create_collection(
                    collection_name = collection_name,
                    vectors_config = models.VectorParams(
                        size = embedding_size,
                        distance = self.distance_method
                    )
                )

                return True

            except Exception as e:
                return self._return_failure(error_type = VECTOR_DB_CLIENT_ERROR, error = e)

        return self._return_success()


    # ------------------------- Insertion -----------------------
    async def insert_one(
        self,
        collection_name: str,
        record_id: int,
        text: str,
        vector: list[float],
        metadata: dict[str, Any],
    ) -> VectorDBResult:
        """
        Insert a record into the given collection

        Returns:
            VectorDBResult
                - if success -> None
                - if failure -> error & error type
        """

        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed.content:
            return self._return_failure(error_type = VECTOR_DB_ERROR_COLLECTION_NOT_FOUND)

        if not record_id and record_id != 0:
            return self._return_failure(error_type = VECTOR_DB_ERROR_INVALID_DATA)
        
        try:
            self.client.upload_points(
                collection_name = collection_name,
                points = [
                    models.Record(
                        id = [record_id],
                        vector = vector,
                        payload = {
                            "text": text,
                            "metadata": metadata
                        }
                    )
                ]
            )

        except Exception as e:
            return self._return_failure(error_type = VECTOR_DB_CLIENT_ERROR, error = e)

        return self._return_success()

    

    async def insert_many(
        self,
        collection_name: str,
        record_ids: list[int],
        texts: list[str],
        vectors: list[list[float]],
        metadata: list[dict[str, Any]],
        batch_size: int = 50
    ) -> VectorDBResult:
        """
        Insert records into the given collection

        Args:
            collection_name (str) : collection name to insert in
            record_ids      (list): list of record IDs to store
            texts           (list): list of texts to store
            vectors         (list): list of vectors
            metadata        (list): list of metadata
            batch_size      (int) : batch size while inserting

        Returns:
            VectorDBResult
                - if success -> None
                - if failure -> error & error type
        """

        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed.content:
            return self._return_failure(error_type = VECTOR_DB_ERROR_COLLECTION_NOT_FOUND)

        if len(record_ids) != len(texts) or len(vectors) != len(texts):
            return self._return_failure(error_type = VECTOR_DB_ERROR_INVALID_DATA)


        # insertion
        for i in range(0, len(texts), batch_size):
            batch_ids = record_ids[i : i + batch_size]
            batch_texts = texts[i : i + batch_size]
            batch_vectors = vectors[i : i + batch_size]
            batch_metadata = metadata[i : i + batch_size]


            batch_records = [
                models.Record(
                    id = batch_ids[x],
                    vector = batch_vectors[x],
                    payload = {
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
                return self._return_failure(error_type = VECTOR_DB_CLIENT_ERROR, error = e)
        
        return self._return_success()
    


    # searching
    async def search_by_vector(
        self,
        collection_name: str,
        vector: list[float],
        limit: int = 5
    ) -> VectorDBResult:
        """
        Insert records into the given collection

        Returns:
            VectorDBResult
                - if success -> content represents the list[Retrieved Chunks]
                - if failure -> error & error type
        """

        is_collection_existed = await self.is_collection_existed(collection_name)
        if not is_collection_existed.content:
            return self._return_failure(error_type = VECTOR_DB_ERROR_COLLECTION_NOT_FOUND)

        try:
            points = self.client.query_points(
                collection_name = collection_name,
                query = vector,
                limit = limit
            ).points

        except Exception as e:
            return self._return_failure(error_type = VECTOR_DB_CLIENT_ERROR, error = e)


        return self._return_success(
            content = [
                RetrievedChunk(**{
                    "text": point.payload["text"],
                    "score": point.score
                })
                for point in points
            ] 
        )
        
        



