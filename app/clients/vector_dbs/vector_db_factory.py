from .vector_db_clients import QDrantVDBClient, PGVectorVDBClient
from .config import (
    VectorDBProviders
)


from helpers.config import Settings

from controllers import BaseController
from sqlalchemy.ext.asyncio import AsyncSession

class VectorDBFactory:
    def __init__(self, config: Settings, db_client: AsyncSession):
        self.config = config
        self.base_controller = BaseController()
        self.db_client = db_client

    def create_vector_db(self, provider: str) -> QDrantVDBClient | PGVectorVDBClient:
        """
        Create & Returns a Vector DB Client

        Args:
            provide (str): The name of the provider. Allowed [qdrant - pgvector]

        Returns:
            the corresponding Vector DB Client | None if the provider is not valid
        """
        if provider == VectorDBProviders.PROVIDER_QDRANT.value:
            return QDrantVDBClient(
                db_path             = self.base_controller.get_vector_database_path(self.config.VECTOR_DB_NAME),
                distance_method     = self.config.VECTOR_DB_DISTANCE_METHOD,
                default_vector_size = self.config.EMBEDDING_SIZE,
            )

        if provider == VectorDBProviders.PROVIDER_PGVEVTOR.value:
            return PGVectorVDBClient(
                db_client           =  self.db_client,
                default_vector_size = self.config.EMBEDDING_SIZE,
                distance_method     = self.config.VECTOR_DB_DISTANCE_METHOD,
                index_threshold     = self.config.PGVECTOR_INDEXING_THRESHOLD
            )
        

        return None