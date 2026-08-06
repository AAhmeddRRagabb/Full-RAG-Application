from .BaseController import BaseController
from models.db_schemas import DataChunk

from stores.vector_dbs import QDrantProvider
from stores.llm_agents import GoogleProvider, GroqProvider, HuggingFaceProvider

import json
from stores.llm_agents.llm_enums import TextTypesEnum

class RetrievalController(BaseController):
    # -------------------- Setup ------------------------- #
    def __init__(
        self,
        vector_db_client: QDrantProvider,
        embedding_client: GoogleProvider | GroqProvider | HuggingFaceProvider,
    ):
        super().__init__()

        self.vector_db_client = vector_db_client
        self.embedding_client = embedding_client

    
    def get_collection_name(self, project_name: str) -> str:
        return f"collection_{project_name}_{self.vector_db_client.default_vector_size}".strip()
    
    # ------------------ Dealing with VectorDB ------------ #
    async def reset_vector_db_collection(self, project_name: str):
        collection_name = self.get_collection_name(project_name = project_name)
        return await self.vector_db_client.delete_collection(collection_name = collection_name)
    
    async def get_vector_db_collection_info(self, project_name: str):
        collection_name = self.get_collection_name(project_name = project_name)
        collection_info = await self.vector_db_client.get_collection_info(collection_name = collection_name)

        return json.loads(
            json.dumps(collection_info, default = lambda x: x.__dict__)
        )
    

    async def create_collection(self, project_name: str, do_reset: bool = False):
        collection_name = self.get_collection_name(project_name = project_name)
        await self.vector_db_client.create_collection(
            collection_name = collection_name,
            embedding_size = self.embedding_client.embedding_size,
            do_reset = do_reset
        )

    async def insert_into_vector_db(
        self,
        project_name: str,
        chunks: list[DataChunk],
        chunks_ids: list[int],
    ):
        # get collection
        collection_name = self.get_collection_name(project_name = project_name)
        
        # prepare chunks 
        texts = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]
        vectors = self.embedding_client.embed_text(text = texts, text_type = TextTypesEnum.DOCUMENT.value) 
        

        # insert
        is_inserted = await self.vector_db_client.insert_many(
            collection_name = collection_name,
            record_ids = chunks_ids,
            texts = texts,
            vectors = vectors,
            metadata = metadata
        )

        return is_inserted
    

    async def search_vector_db_collection(
        self,
        project_name: str,
        text: str,
        limit: int = 5,
        encode_as_json: bool = False
    ):
        collection_name = self.get_collection_name(project_name = project_name)

        # embed query
        vectors = self.embedding_client.embed_text(
            text = text,
            text_type = TextTypesEnum.SEARCH_QUERY.value,
        )

        if not vectors or len(vectors) == 0:
            return False

        query_vector = vectors[0]

        # search query
        retrieved = await self.vector_db_client.search_by_vector(
            collection_name = collection_name,
            vector = query_vector,
            limit = limit
        )

        if not retrieved:
            return False

        if not encode_as_json:
            return retrieved
        
        return json.loads(
            json.dumps(retrieved, default = lambda x: x.__dict__)
        )
    

    

