
# ----------------------------------------------------
# Asset Class (resources). It can be
# - File
# - URL
# - ...
# ----------------------------------------------------



from typing import Optional
from bson.objectid import ObjectId
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

class Asset(BaseModel):
    id: Optional[ObjectId] = Field(None, alias = "_id")
    asset_project_id: ObjectId
    asset_name: str = Field(..., min_length = 1)
    asset_type: str = Field(..., min_length = 1)
    asset_size: int = Field(ge = 0, default = None)
    asset_config: dict = Field(default = None)
    asset_pushed_at: datetime = Field(default = datetime.now(timezone.utc))

    model_config = ConfigDict(
        arbitrary_types_allowed = True,
        populate_by_name = True,
    )

    @staticmethod
    def get_indexes():
        return [
            {
                "key": [
                    ("project_id", 1)
                ],

                "name": "asset_project_id_index_1",
                "unique": False
            },

            {
                "key": [
                    ("project_id", 1),
                    ("asset_name", 1)
                ],

                "name": "asset_project_id_name_index_1",
                "unique": True
            }
        ]