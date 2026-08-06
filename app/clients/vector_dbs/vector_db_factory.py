from .dbs_providers import QDrantProvider, PGVectorProvider
from .dbs_enums import VectorDBProvidersEnum
from helpers.config import Settings

from controllers import BaseController
from sqlalchemy.ext.asyncio import AsyncSession

class VectorDBFactory:
    def __init__(self, config: Settings, db_client: AsyncSession):
        self.config = config
        self.base_controller = BaseController()
        self.db_client = db_client

    def create_vector_db(self, provider: str) -> QDrantProvider:
        if provider == VectorDBProvidersEnum.PROVIDER_QDRANT.value:
            return QDrantProvider(
                db_path = self.base_controller.get_vector_database_path(self.config.VECTOR_DB_NAME),
                distance_method = self.config.VECTOR_DB_DISTANCE_METHOD
            )

        if provider == VectorDBProvidersEnum.PROVIDER_PGVEVTOR.value:
            return PGVectorProvider(
                db_client = self.db_client,
                default_vector_size = self.config.EMBEDDING_SIZE,
                distance_method = self.config.VECTOR_DB_DISTANCE_METHOD,
                index_threshold = self.config.PGVECTOR_INDEXING_THRESHOLD
            )
        

        raise NotImplementedError