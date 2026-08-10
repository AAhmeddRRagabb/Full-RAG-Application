from .minirag_base import SQLAlchemyBase

from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from sqlalchemy.orm import relationship

from pydantic import BaseModel


class DataChunk(SQLAlchemyBase):
    # table name
    __tablename__ = 'chunks'

    # columns
    chunk_id   = Column(Integer, primary_key = True, autoincrement = True)
    chunk_uuid = Column(UUID(as_uuid = True), unique = True, default = uuid.uuid4, nullable = False)

    chunk_text = Column(String, nullable = False)
    chunk_order = Column(Integer, nullable = False)
    chunk_metadata = Column(
        JSONB, # binary json: fast in reading [data alreay in binary]
        nullable = True
    )

    chunk_project_id = Column(Integer, ForeignKey('projects.project_id'), nullable = False)
    chunk_asset_id = Column(Integer, ForeignKey('assets.asset_id'), nullable = False)


    project = relationship("Project", back_populates = 'chunks')
    asset = relationship("Asset", back_populates = 'chunks')


    # indexing
    __table_args__ = (
        Index('ix_chunk_project_id', chunk_project_id),
        Index('ix_chunk_asset_id'  ,  chunk_asset_id)
    )

class RetrievedChunk(BaseModel):
    text: str
    score: float
