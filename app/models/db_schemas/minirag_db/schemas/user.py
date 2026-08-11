
from .minirag_base import SQLAlchemyBase

from sqlalchemy import Column, Integer, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID

import uuid


from sqlalchemy.orm import relationship
class User(SQLAlchemyBase):
    # table name
    __tablename__ = 'users'

    # columns
    user_id = Column(Integer, primary_key = True, autoincrement = True)
    user_uuid = Column(UUID(as_uuid = True), unique = True, default = uuid.uuid4, nullable = False)
    user_name = Column(String, unique = True, nullable = False)

    joined_at = Column(DateTime(timezone = True), server_default = func.now(), nullable = False)

    # linking
    assets = relationship("Asset", back_populates = "user")
    chunks = relationship('DataChunk', back_populates = 'user')
