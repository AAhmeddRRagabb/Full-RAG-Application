from .vector_db_clients import QDrantVDBClient, PGVectorVDBClient
from .config import (
    VectorDBProviders
)


from helpers.config import Settings
from models.enums import ResponsesEnum
from models.system_schemas import ComponentResult

from controllers import BaseController
from sqlalchemy.ext.asyncio import AsyncSession

class VectorDBFactory:
    def __init__(self, config: Settings, db_client: AsyncSession):
        self.config = config
        self.base_controller = BaseController()
        self.db_client = db_client

    def create_vector_db(self, provider: str) -> ComponentResult:
        """
        Create & Returns a Vector DB Client

        Args:
            provide (str): The name of the provider. Allowed [qdrant - pgvector]

        Returns:
            ComponentResult:
                if success -> content: the corresponding Vector DB Client
                if failure -> error & respone message
        """
        if provider == VectorDBProviders.PROVIDER_QDRANT.value:
            try:
                return ComponentResult(
                    success = True,
                    content = QDrantVDBClient(
                        db_path             = self.base_controller.get_vector_database_path(self.config.VECTOR_DB_NAME),
                        distance_method     = self.config.VECTOR_DB_DISTANCE_METHOD,
                        default_vector_size = self.config.EMBEDDING_SIZE,
                    )
                )
            except Exception as e:
                return ComponentResult(
                    success = False,
                    error = e,
                    message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value
                )

        if provider == VectorDBProviders.PROVIDER_PGVEVTOR.value:
            try:
                return ComponentResult(
                    success = True,
                    content = PGVectorVDBClient(
                        db_client           =  self.db_client,
                        default_vector_size = self.config.EMBEDDING_SIZE,
                        distance_method     = self.config.VECTOR_DB_DISTANCE_METHOD,
                        index_threshold     = self.config.PGVECTOR_INDEXING_THRESHOLD
                    )
                )
            except Exception as e:
                return ComponentResult(
                    success = False,
                    error = e,
                    message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value
                )
        

        return ComponentResult(
            success = False,
            error = provider,
            message = ResponsesEnum.VECTOR_DB_INNER_ERROR.value
        )
