
import uuid
from datetime import datetime
from pydantic import BaseModel

class SessionData(BaseModel):
    user_uuid: uuid.UUID

    created_at: datetime
    expires_at: datetime

    session_version: int
