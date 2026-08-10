import json
from helpers.config import get_settings
from .base_controller import BaseController, ControllerResult

from models.enums import ResponsesEnum
from models.db_schemas import DataChunk

# vector db utils
from clients.vector_dbs.vector_db_clients import (
    QDrantVDBClient,
    PGVectorVDBClient
)

from clients.vector_dbs.config import (
    VECTOR_DB_CLIENT_ERROR,
    VECTOR_DB_ERROR_COLLECTION_NOT_FOUND,
    VECTOR_DB_ERROR_INVALID_DATA,
    VectorDBResult
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
    def _parse_vector_db_result(self, vector_db_result: VectorDBResult, return_json: bool = False) -> ControllerResult:
        if vector_db_result.success:
            return self._return_success(
                content = json.dumps(
                    vector_db_result.content,
                    default = lambda x : x.__dict__
                ) if return_json else vector_db_result.content
            )
            

        if vector_db_result.error_type == VECTOR_DB_CLIENT_ERROR:
            return self._return_failure(error = vector_db_result.error, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

        if vector_db_result.error_type == VECTOR_DB_ERROR_COLLECTION_NOT_FOUND:
            return self._return_failure(error = ResponsesEnum.VECTOR_DB_COLLECTION_NOT_FOUND.value, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)

        if vector_db_result.error_type == VECTOR_DB_ERROR_INVALID_DATA:
            return self._return_failure(error = ResponsesEnum.VECTOR_DB_INVALID_DATA.value, message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value)



    def get_collection_name(self, project_name: str) -> str:
        return f"collection_{project_name}_{self.vector_db_client.default_vector_size}".strip()



    async def get_vector_db_collection_info(self, project_name: str) -> ControllerResult:
        """
        Returns:
            ControllerResults:
                if success -> content: Json-serializable collection info
                if failure -> error 
        """
        collection_name = self.get_collection_name(project_name = project_name)

        collection_info_result = await self.vector_db_client.get_collection_info(collection_name = collection_name)
        return self._parse_vector_db_result(collection_info_result)



    async def create_collection(self, project_name: str, do_reset: bool = False):
        collection_name = self.get_collection_name(project_name = project_name)

        creation_result = await self.vector_db_client.create_collection(
            collection_name = collection_name,
            embedding_size = self.embedding_client.embedding_size,
            do_reset = do_reset
        )

        return self._parse_vector_db_result(creation_result)


    async def delete_collection(self, project_name: str) -> ControllerResult:
        collection_name = self.get_collection_name(project_name = project_name)
        delete_result = await self.vector_db_client.delete_collection(collection_name = collection_name)
        return self._parse_vector_db_result(delete_result)


    async def insert_into_vector_db(
        self,
        project_name: str,
        chunks      : list[DataChunk],
        chunks_ids  : list[int],
    ):
        collection_name = self.get_collection_name(project_name = project_name)
            
        # prepare chunks 
        texts    = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]
        vectors  = self.embedding_client.embed_text(
            text = texts, 
            prompt_type = LLMsGeneralEmbeddingQueryTypes.DOCUMENT.value,
        ) 
            
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
        project_name: str,
        text: str,
        limit: int = 5,
        encode_as_json: bool = False
    ):
        collection_name = self.get_collection_name(project_name = project_name)

        # embed query
        vectors = self.embedding_client.embed_text(text = text, prompt_type = LLMsGeneralEmbeddingQueryTypes.SEARCH_QUERY.value,)
        if not vectors or len(vectors) == 0:
            return False

        query_vector = vectors[0]

        # search query
        retrieved = await self.vector_db_client.search_by_vector(
            collection_name = collection_name,
            vector = query_vector,
            limit = limit
        )

        return self._parse_vector_db_result(retrieved, return_json = encode_as_json)

    # -------------------------------------------- Generation Functionalities --------------------------------------------- #

    def _get_system_prompt_role(self) -> str:
        if isinstance(self.generation_client, GroqLLMClient):
            return LLMsGenerationMessageTypes.GROQ_SYSTEM_MESSAGE.value

        if isinstance(self.generation_client, HuggingfaceLLMClient):
            return LLMsGenerationMessageTypes.HF_SYSTEM_MESSAGE.value

        if isinstance(self.generation_client, GoogleLLMClient):
            return LLMsGenerationMessageTypes.GOOGLE_SYSTEM_MESSAGE.value


    async def answer_rag_query(
        self, 
        project_name: str,
        query: str,
        retrieval_limit: str,
    ) -> ControllerResult:
        # retrieve relevant
        relevant_documents_result = await self.search_vector_db_collection(
            project_name = project_name,
            text = query,
            limit = retrieval_limit
        )
    
        if not relevant_documents_result.success:
            return self._return_failure(error = relevant_documents_result.error, message = relevant_documents_result.message)

        relevant_documents = relevant_documents_result.content
            
        # construct prompts
        system_prompt = self.prompt_template_parser.get_prompt("rag", "system_prompt")
    
        documents_prompt = "\n".join([
            self.prompt_template_parser.get_prompt("rag", "document_prompt", {
                "doc_num": idx,
                "doc_text": self.generation_client.pre_process_input_prompt(doc.text)
            })
            for idx, doc in enumerate(relevant_documents, start = 1)
        ])
    
        footer_prompt = self.prompt_template_parser.get_prompt("rag", "footer_prompt", {
            "query": query
        })
    
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
            return self._return_failure()


        return self._return_success(content = {
            "answer"      : answer,
            "full_prompt" : full_prompt,
            "chat_history": chat_history
        })

        