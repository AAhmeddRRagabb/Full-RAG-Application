from pydantic import BaseModel
from typing import Optional

class PushChunksRequest(BaseModel):
    do_reset: Optional[int] = 0