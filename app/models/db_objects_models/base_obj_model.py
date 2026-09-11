# -------------------------------------------------------
# Building a Base Model to store/load/act on database 
# -------------------------------------------------------
from typing import Any
from helpers.config import get_settings
import logging

class BaseObjModel:
    def __init__(self, db_client: object):
        self.db_client = db_client
        self.settings = get_settings()
        self.logger = logging.getLogger("uvicorn")

