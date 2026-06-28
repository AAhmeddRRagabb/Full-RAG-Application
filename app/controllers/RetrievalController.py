from .BaseController import BaseController
from models.db_schemas import DataChunk

from stores.vector_dbs import QDrantProvider
from stores.llm_agents import GoogleProvider, GroqProvider

import json
from stores.llm_agents.llm_enums import TextTypesEnum

class RetrievalController(BaseController):
    # -------------------- Setup ------------------------- #
    def __init__(
        self,
        vector_db_client: QDrantProvider,
        embedding_client: GoogleProvider | GroqProvider,
        generation_client: GoogleProvider | GroqProvider,
    ):
        super().__init__()

        self.vector_db_client = vector_db_client
        self.embedding_client = embedding_client
        self.generation_client = generation_client

    
    def get_collection_name(self, project_name: str) -> str:
        return f"collection_{project_name}".strip()
    
    # ------------------ Dealing with VectorDB ------------ #
    def reset_vector_db_collection(self, project_name: str):
        collection_name = self.get_collection_name(project_name = project_name)
        return self.vector_db_client.delete_collection(collection_name = collection_name)
    
    def get_vector_db_collection_info(self, project_name: str):
        collection_name = self.get_collection_name(project_name = project_name)
        collection_info = self.vector_db_client.get_collection_info(collection_name = collection_name)

        return json.loads(
            json.dumps(collection_info, default = lambda x: x.__dict__)
        )
    

    def create_collection(self, project_name: str, do_reset: bool = False):
        collection_name = self.get_collection_name(project_name = project_name)
        self.vector_db_client.create_collection(
            collection_name = collection_name,
            embedding_size = self.embedding_client.embedding_size,
            do_reset = do_reset
        )

    def insert_into_vector_db(
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
        vectors = [
            self.embedding_client.embed_text(text = c.chunk_text, text_type = TextTypesEnum.DOCUMENT.value) 
            for c in chunks
        ]

        # insert
        is_inserted = self.vector_db_client.insert_many(
            collection_name = collection_name,
            record_ids = chunks_ids,
            texts = texts,
            vectors = vectors,
            metadata = metadata
        )

        return is_inserted
    

    def search_vector_db_collection(
        self,
        project_name: str,
        text: str,
        limit: int = 5
    ):
        collection_name = self.get_collection_name(project_name = project_name)

        # embed query
        vector = self.embedding_client.embed_text(
            text = text,
            text_type = TextTypesEnum.SEARCH_QUERY.value,
        )

        if not vector or len(vector) == 0:
            return False

        # search query
        retrieved = self.vector_db_client.search_by_vector(
            collection_name = collection_name,
            vector = vector,
            limit = limit
        )

        if not retrieved:
            return False
        
        return json.loads(
            json.dumps(retrieved, default = lambda x: x.__dict__)
        )
    

    

