import json
from .base_controller import BaseController

from models.enums import ResponsesEnum
from models.db_schemas import DataChunk
from models.system_schemas import RetrievedChunk

# vector db utils
from clients.vector_dbs.vector_db_clients import PGVectorVDBClient


# llms utils
from clients.llms.llm_clients import (
    GoogleLLMClient,
    GroqLLMClient,
    HuggingfaceLLMClient
)

from clients.llms.config import LLMsGeneralEmbeddingQueryTypes, LLMsGenerationMessageTypes
from fastapi.encoders import jsonable_encoder

class VectorDBController(BaseController):
    """
    Controls Vector database functionalities:
        * creating / deleting collections.
        * inserting into collections.
        * retrieving relevant documents from collections.
    """
    # -------------------- Setup ------------------------- #
    def __init__(
        self,
        vector_db_client      : PGVectorVDBClient | None = None,
        embedding_client      : GoogleLLMClient | HuggingfaceLLMClient | None = None ,
    ):
        super().__init__()

        self.vector_db_client  = vector_db_client
        self.embedding_client  = embedding_client


    # -------------------------------------------- Vector DB Functionalities --------------------------------------------- #
    def get_collection_name(self, user_name: str) -> str:
        """
        Returns:
            str: vector database collection name for the given user.
        """
        return f"collection_{user_name}_{self.vector_db_client.default_vector_size}".strip()


    async def get_vector_db_collection_info(self, user_name: str) -> dict | None:
        """
        Returns:
            if success -> collection info  
            if failure or not existing collection -> None 
        """
        collection_name = self.get_collection_name(user_name = user_name)
        return jsonable_encoder(await self.vector_db_client.get_collection_info(collection_name = collection_name))

        
    async def create_collection(self, user_name: str, do_reset: bool = False) -> bool:
        """
        Create a collection with the given name & embedding size

        Returns:
            a bool indicates whether the collection was created successfully or not.
        """

        collection_name = self.get_collection_name(user_name = user_name)

        return await self.vector_db_client.create_collection(
            collection_name = collection_name,
            embedding_size = self.embedding_client.embedding_size,
            do_reset = do_reset
        )

    
    async def delete_collection(self, user_name: str) -> bool:
        """
        Delete the given collection

        Returns:
            a bool indicates whether the collection was deleted successfully or not.
        """
        collection_name = self.get_collection_name(user_name = user_name)
        return await self.vector_db_client.delete_collection(collection_name = collection_name)


    async def insert_chunks_into_vector_db(
        self,
        user_name   : str,
        chunks      : list[DataChunk],
        chunks_ids  : list[int],
    ) -> bool:
        """
        Returns:
            a bool indicates whether the records were inserted successfully or not.
        """

        collection_name = self.get_collection_name(user_name = user_name)
            
        # prepare chunks 
        texts    = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]

        # embed documen
        embeddings  = self.embedding_client.embed_text(
            text = texts, 
            prompt_type = LLMsGeneralEmbeddingQueryTypes.DOCUMENT.value,
        )

        if not embeddings or len(embeddings) == 0:
            return False
        
            
        # insert
        return await self.vector_db_client.insert_many(
            collection_name = collection_name,
            record_ids = chunks_ids,
            texts = texts,
            vectors = embeddings,
            metadata = metadata
        )
    

    async def search_vector_db_collection(
        self,
        user_name     : str,
        text          : str,
        limit         : int = 5,
        chunk_ids     : list[int] | None = None,
        encode_as_json: bool = False 
    ) -> list[RetrievedChunk]:
        """
        Args:
            user_name     : user_name to access the user_collection
            text          : text to use in searching
            limit         : number of search results to retrieve
            chunk_ids     : list of chunk ids to only search in them.
            encode_as_json: whether to serialize results or not  

        Returns:  
            if success -> list of retrieved chunks       
            if failure -> None 
        """
        collection_name = self.get_collection_name(user_name = user_name)

        # embed query
        embeddings = self.embedding_client.embed_text(
            text = text,
            prompt_type = LLMsGeneralEmbeddingQueryTypes.SEARCH_QUERY.value,
        )


        if not embeddings or len(embeddings) == 0:
            return None

        query_vector = embeddings[0]

        # Search query
        retrieved = await self.vector_db_client.search_by_vector(
            collection_name = collection_name,
            vector = query_vector,
            limit = limit,
            chunk_ids = chunk_ids
        )

        if encode_as_json:
            return jsonable_encoder(retrieved)

        return retrieved


    

        