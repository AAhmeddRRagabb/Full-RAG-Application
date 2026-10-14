import logging

from core.system_settings import get_system_settings as get_settings

class BaseObjModel:
    def __init__(self, db_client: object):
        self.db_client = db_client
        self.settings = get_settings()
        self.logger = logging.getLogger("uvicorn")

