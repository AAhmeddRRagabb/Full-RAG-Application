import json
from .base_controller import BaseController

from models.system_schemas import ComponentResult
from models.enums import ResponsesEnum
from models.db_schemas import DataChunk

# vector db utils
from clients.vector_dbs.vector_db_clients import (
    QDrantVDBClient,
    PGVectorVDBClient
)

# llms utils
from clients.llms.llm_clients import (
    GoogleLLMClient,
    GroqLLMClient,
    HuggingfaceLLMClient
)
from clients.llms.prompt_templates import PromptTemplateParser

from clients.llms.config import LLMsGeneralEmbeddingQueryTypes, LLMsGenerationMessageTypes


class NLPController(BaseController):
    """
    Controller for vector database and RAG generation workflows.
    """
    # -------------------- Setup ------------------------- #
    def __init__(
        self,
        vector_db_client      : QDrantVDBClient | PGVectorVDBClient | None = None,
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
    def _parse_vector_db_result(self, vector_db_result: ComponentResult, return_json: bool = False, message_on_success: str | None = None) -> ComponentResult:
        """
        Returns:
            ComponentResult:
                if success -> content: parsed vector database client content
                if failure -> error & respone message
        """
        if vector_db_result.success:
            return self._return_success(
                content = json.dumps(
                    vector_db_result.content,
                    default = lambda x : x.__dict__
                ) if return_json else vector_db_result.content,
                message = message_on_success
            )
            

        return self._return_failure(error = vector_db_result.error, message = vector_db_result.message)



    def get_collection_name(self, user_name: str) -> str:
        """
        Returns:
            str: vector database collection name for the given user.
        """
        return f"collection_{user_name}_{self.vector_db_client.default_vector_size}".strip()



    async def get_vector_db_collection_info(self, user_name: str) -> ComponentResult:
        """
        Returns:  
            ComponentResult:  
                if success -> content: Json-serializable collection info
                if failure -> error 
        """
        collection_name = self.get_collection_name(user_name = user_name)

        collection_info_result = await self.vector_db_client.get_collection_info(collection_name = collection_name)
        return self._parse_vector_db_result(collection_info_result)


    async def create_collection(self, user_name: str, do_reset: bool = False) -> ComponentResult:
        """
        Returns:  
            ComponentResult:  
                if success -> content: None  
                if failure -> error 
        """

        collection_name = self.get_collection_name(user_name = user_name)

        creation_result = await self.vector_db_client.create_collection(
            collection_name = collection_name,
            embedding_size = self.embedding_client.embedding_size,
            do_reset = do_reset
        )

        return self._parse_vector_db_result(creation_result)


    async def delete_collection(self, user_name: str) -> ComponentResult:
        """
        Returns:  
            ComponentResult:  
                if success -> content: None  
                if failure -> error 
        """
        collection_name = self.get_collection_name(user_name = user_name)
        delete_result = await self.vector_db_client.delete_collection(collection_name = collection_name)
        return self._parse_vector_db_result(delete_result)


    async def insert_into_vector_db(
        self,
        user_name: str,
        chunks      : list[DataChunk],
        chunks_ids  : list[int],
    ) -> ComponentResult:
        """
        Returns:  
            ComponentResult:  
                if success -> content: None  
                if failure -> error 
        """

        collection_name = self.get_collection_name(user_name = user_name)
            
        # Prepare chunks 
        texts    = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]
        vectors_result  = self.embedding_client.embed_text(
            text = texts, 
            prompt_type = LLMsGeneralEmbeddingQueryTypes.DOCUMENT.value,
        )

        if not vectors_result.success:
            return self._return_failure(error = vectors_result.error, message = vectors_result.message)

        vectors = vectors_result.content
            
        # insert
        is_inserted = await self.vector_db_client.insert_many(
            collection_name = collection_name,
            record_ids = chunks_ids,
            texts = texts,
            vectors = vectors,
            metadata = metadata
        )
    
        return self._parse_vector_db_result(is_inserted)


    async def search_vector_db_collection(
        self,
        user_name: str,
        text: str,
        limit: int = 5,
        encode_as_json: bool = False
    ) -> ComponentResult:
        """
        Returns:  
            ComponentResult:  
                if success -> content: list of retrieved chunks    
                if failure -> error 
        """
        collection_name = self.get_collection_name(user_name = user_name)

        # Embed query
        vectors_result = self.embedding_client.embed_text(
            text = text,
            prompt_type = LLMsGeneralEmbeddingQueryTypes.SEARCH_QUERY.value,
        )

        if not vectors_result.success:
            return self._return_failure(error = vectors_result.error, message = vectors_result.message)

        vectors = vectors_result.content
        if not vectors or len(vectors) == 0:
            return self._return_failure(message = ResponsesEnum.GENERATION_ERROR_WHILE_CALLING_AGENT.value)

        query_vector = vectors[0]

        # Search query
        retrieved = await self.vector_db_client.search_by_vector(
            collection_name = collection_name,
            vector = query_vector,
            limit = limit
        )

        return self._parse_vector_db_result(retrieved, return_json = encode_as_json)

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
        user_name: str,
        query: str,
        retrieval_limit: str,
    ) -> ComponentResult:
        """
        Returns:  
            ComponentResult:  
                if success -> content: list of retrieved chunks    
                if failure -> error 
        """
        # Retrieve relevant
        relevant_documents_result = await self.search_vector_db_collection(
            user_name = user_name,
            text = query,
            limit = retrieval_limit
        )
    
        if not relevant_documents_result.success:
            return self._return_failure(error = relevant_documents_result.error, message = relevant_documents_result.message)

        relevant_documents = relevant_documents_result.content
            
        # construct prompts
        system_prompt_result = self.prompt_template_parser.get_prompt("rag", "system_prompt")
        if not system_prompt_result.success:
            return self._return_failure(error = system_prompt_result.error, message = system_prompt_result.message)

        system_prompt = system_prompt_result.content
    
        document_prompts = []
        for idx, doc in enumerate(relevant_documents, start = 1):
            document_prompt_result = self.prompt_template_parser.get_prompt("rag", "document_prompt", {
                "doc_num": idx,
                "doc_text": self.generation_client.pre_process_input_prompt(doc.text)
            })

            if not document_prompt_result.success:
                return self._return_failure(error = document_prompt_result.error, message = document_prompt_result.message)

            document_prompts.append(document_prompt_result.content)

        documents_prompt = "\n".join(document_prompts)
    
        footer_prompt_result = self.prompt_template_parser.get_prompt("rag", "footer_prompt", {
            "query": query
        })

        if not footer_prompt_result.success:
            return self._return_failure(error = footer_prompt_result.error, message = footer_prompt_result.message)

        footer_prompt = footer_prompt_result.content
    
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
    
        answer_result = self.generation_client.generate_text(
            user_prompt = full_prompt,
            chat_history = chat_history
        )
    
        if not answer_result.success:
            return self._return_failure(error = answer_result.error, message = answer_result.message)

        return self._return_success(content = {
            "answer"      : answer_result.content,
            "full_prompt" : full_prompt,
            "chat_history": chat_history
        })

        
