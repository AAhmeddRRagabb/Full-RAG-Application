from .vector_db_clients import PGVectorVDBClient
from .config import (
    VectorDBProviders
)


from helpers.config import Settings
from models.enums import ResponsesEnum

from controllers import BaseController
from sqlalchemy.ext.asyncio import AsyncSession

class VectorDBFactory:
    def __init__(self, config: Settings, db_client: AsyncSession):
        self.config = config
        self.base_controller = BaseController()
        self.db_client = db_client

    def create_vector_db(self, provider: str) -> PGVectorVDBClient | None:
        """
        Create & Returns a Vector DB Client

        Args:
            provider (str): The name of the provider. Allowed [pgvector]

        Returns:
            if success -> the client requested
            if failure -> None
        """

        if provider == VectorDBProviders.PROVIDER_PGVEVTOR.value:
            return PGVectorVDBClient(
                db_client           =  self.db_client,
                default_vector_size = self.config.EMBEDDING_SIZE,
                distance_method     = self.config.VECTOR_DB_DISTANCE_METHOD,
                index_threshold     = self.config.PGVECTOR_INDEXING_THRESHOLD
            )
                

        return None
