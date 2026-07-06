from .BaseController import BaseController
from models.db_schemas import DataChunk

from stores.vector_dbs import QDrantProvider
from stores.llm_agents import GoogleProvider, GroqProvider, HuggingFaceProvider

import json
from stores.llm_agents.llm_enums import TextTypesEnum

from .RetrievalController import RetrievalController

from stores.llm_agents.prompt_templates import PromptTemplateParser
class GenerationController(BaseController):
    # -------------------- Setup ------------------------- #
    def __init__(
        self,
        vector_db_client: QDrantProvider,
        generation_client: GoogleProvider | GroqProvider | HuggingFaceProvider,
        embedding_client: GoogleProvider  | HuggingFaceProvider,
        prompt_template_parser: PromptTemplateParser
    ):
        super().__init__()

        self.vector_db_client = vector_db_client
        self.generation_client = generation_client
        self.embedding_client = embedding_client
        self.prompt_template_parser = prompt_template_parser

    
    def get_collection_name(self, project_name: str) -> str:
        return f"collection_{project_name}".strip()
    
    # ------------------ Dealing with VectorDB ------------ #
    def answer_rag_query(
        self, 
        project_name: str,
        query: str,
        limit: str,
    ):
        # retrieve relevant
        relevant_documents = RetrievalController(
            vector_db_client = self.vector_db_client,
            embedding_client = self.embedding_client
        ).search_vector_db_collection(project_name = project_name, text = query, limit = limit)

        if not relevant_documents:
            return {
                "answer": None,
                "full_prompt": None,
                "chat_history": None
            }
        
        # construct prompts
        system_prompt = self.prompt_template_parser.get_prompt("rag", "system_prompt")

        documents_prompt = "\n".join([
            self.prompt_template_parser.get_prompt("rag", "document_prompt", {
                "doc_num": idx,
                "doc_text": doc.text
            })
            for idx, doc in enumerate(relevant_documents, start = 1)
        ])

        footer_prompt = self.prompt_template_parser.get_prompt("rag", "footer_prompt", {
            "query": query
        })


        chat_history = [
            self.generation_client.construct_prompt(
                prompt = system_prompt,
                role = self.generation_client.message_roles_enum.SYSTEM_MESSAGE.value
            )
        ]

        full_prompt = "\n\n".join([
            documents_prompt,
            footer_prompt,
        ])

        answer = self.generation_client.generate_text(
            prompt = full_prompt,
            chat_history = chat_history
        )

        if not answer:
            return {
                "answer": None,
                "full_prompt": None,
                "chat_history": None
            }
        
        return {
            "answer": answer,
            "full_prompt": full_prompt,
            "chat_history": chat_history
        }