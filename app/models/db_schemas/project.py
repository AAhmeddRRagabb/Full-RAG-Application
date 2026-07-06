# ------------------------------------------------
# Project Class
# ------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from bson.objectid import ObjectId

class Project(BaseModel):
    id: Optional[ObjectId] = Field(default = None, alias = "_id")
    project_name: str = Field(
        ...,
        min_length = 1,
    )

    model_config = ConfigDict(
        arbitrary_types_allowed = True,
        populate_by_name = True,
    )

    @property
    def _id(self):
        return self.id

    @_id.setter
    def _id(self, value):
        self.id = value

    @field_validator("project_name")
    def validate_project_name(cls, value: str) -> str:
        if not value.isalnum():
            raise ValueError("Project id must be alphanumeric")
        return value
    
    # indexing for faster searching
    @staticmethod
    def get_indexes():
        return [
            {
                "key" : [
                    ("project_name", 1)  # index by project id & 1 -> asc, | -1 desc
                ],

                "name": "project_name_index_1",   # unique name
                "unique": True   # should the index itself should be unique or not
            }
        ]
    