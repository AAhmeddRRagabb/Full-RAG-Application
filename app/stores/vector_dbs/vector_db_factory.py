from .dbs_providers import QDrantProvider
from .dbs_enums import VectorDBProvidersEnum
from helpers.config import Settings

from controllers import BaseController

class VectorDBFactory:
    def __init__(self, config: Settings):
        self.config = config
        self.base_controller = BaseController()

    def create_vector_db(self, provider: str) -> QDrantProvider:
        if provider == VectorDBProvidersEnum.PROVIDER_QDRANT.value:
            return QDrantProvider(
                db_path = self.base_controller.get_vector_database_path(self.config.VECTOR_DB_NAME),
                distance_method = self.config.VECTOR_DB_DISTANCE_METHOD
            )
        

        raise NotImplementedError