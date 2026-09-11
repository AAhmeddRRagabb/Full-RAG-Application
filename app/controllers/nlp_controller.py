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

from clients.llms.prompt_templates import PromptTemplateParser
from clients.llms.config import LLMsGeneralEmbeddingQueryTypes, LLMsGenerationMessageTypes
from fastapi.encoders import jsonable_encoder

class NLPController(BaseController):
    """
    Controller for vector database and RAG generation workflows.
    """
    # -------------------- Setup ------------------------- #
    def __init__(
        self,
        vector_db_client      : PGVectorVDBClient | None = None,
        embedding_client      : GoogleLLMClient | HuggingfaceLLMClient | None = None ,
        generation_client     : GoogleLLMClient | GroqLLMClient | HuggingfaceLLMClient | None = None,
        prompt_template_parser: PromptTemplateParser | None = None
    ):
        super().__init__()

        self.vector_db_client  = vector_db_client
        self.embedding_client  = embedding_client
        self.generation_client = generation_client

        self.prompt_template_parser   = prompt_template_parser

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
        return await jsonable_encoder(self.vector_db_client.get_collection_info(collection_name = collection_name))

        
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
        encode_as_json: bool = False 
    ) -> list[RetrievedChunk]:
        """
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
            limit = limit
        )

        if encode_as_json:
            return jsonable_encoder(retrieved)

        return retrieved

    # -------------------------------------------- Generation Functionalities --------------------------------------------- #

    def _get_system_prompt_role(self) -> str:
        """
        Returns:
            str: provider-specific system prompt role.
        """
        if isinstance(self.generation_client, GroqLLMClient):
            return LLMsGenerationMessageTypes.GROQ_SYSTEM_MESSAGE.value

        if isinstance(self.generation_client, HuggingfaceLLMClient):
            return LLMsGenerationMessageTypes.HF_SYSTEM_MESSAGE.value

        if isinstance(self.generation_client, GoogleLLMClient):
            return LLMsGenerationMessageTypes.GOOGLE_SYSTEM_MESSAGE.value


    async def answer_rag_query(
        self, 
        user_name      : str,
        query          : str,
        retrieval_limit: str,
    ) -> dict | None:
        """
        Returns:
                if success -> dict contains {'answer', 'full_prompt', 'chat_history'}   
                if failure -> None 
        """
        # retrieve relevant
        retrieved = await self.search_vector_db_collection(
            user_name = user_name,
            text = query,
            limit = retrieval_limit
        )
    
        if not retrieved:
            return None

            
        # construct prompts
        system_prompt = self.prompt_template_parser.get_prompt("rag", "system_prompt")
        if not system_prompt:
            self.logger.error("Error Acquiring System Prompt")
            return None

    
        document_prompts = []
        for idx, doc in enumerate(retrieved, start = 1):
            document_prompt = self.prompt_template_parser.get_prompt("rag", "document_prompt", {
                "doc_num": idx,
                "doc_text": self.generation_client.pre_process_input_prompt(doc.text)
            })

            if not document_prompt:
                self.logger.error("Error Acquiring Document Prompt")
                return None

            document_prompts.append(document_prompt)

        documents_prompt = "\n".join(document_prompts)
    
        footer_prompt = self.prompt_template_parser.get_prompt("rag", "footer_prompt", {
            "query": query
        })

        if not footer_prompt:
            self.logger.error("Error Acquiring Footer Prompt")
            return None

        # generation    
        chat_history = [
            self.generation_client.create_prompt(
                prompt = system_prompt,
                role = self._get_system_prompt_role()
            )
        ]
    
        full_prompt = "\n\n".join([
            documents_prompt,
            footer_prompt,
        ])
    
        answer = self.generation_client.generate_text(
            user_prompt = full_prompt,
            chat_history = chat_history
        )

        if not answer:
            self.logger.error("Invalid LLM Answer")
            return None
    


        return {
            "answer"      : answer,
            "full_prompt" : full_prompt,
            "chat_history": chat_history
        }

        
