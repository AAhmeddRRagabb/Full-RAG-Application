# -------------------------------------------------------
# Building a Base Model to store/load/act on database 
# -------------------------------------------------------

from helpers.config import get_settings


class BaseObjModel:
    def __init__(self, db_client: object):
        self.db_client = db_client
        self.settings = get_settings()

        