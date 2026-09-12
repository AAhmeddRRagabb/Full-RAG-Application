from pydantic import BaseModel
from typing import Optional

class PushChunksRequest(BaseModel):
    asset_name: Optional[str] = None
    do_reset: Optional[int] = 0
    page_size: Optional[int] = 50