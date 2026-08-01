from .minirag_base import SQLAlchemyBase

from sqlalchemy import Column, Integer, DateTime, func, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from sqlalchemy.orm import relationship

class Asset(SQLAlchemyBase):
    # table name
    __tablename__ = 'assets'

    # columns
    asset_id = Column(Integer, primary_key = True, autoincrement = True)
    asset_uuid = Column(UUID(as_uuid = True), unique = True, default = uuid.uuid4, nullable = False)

    asset_type = Column(String, nullable = False, default = 'file')
    asset_name = Column(String, nullable = False)
    asset_size = Column(Integer, nullable = True)
    asset_config = Column(
        JSONB, # binary json: fast in reading [data alreay in binary]
        nullable = True
    )

    asset_project_id = Column(Integer, ForeignKey('projects.project_id'), nullable = False)


    # linking
    project = relationship("Project", back_populates = 'assets')
    chunks = relationship('DataChunk', back_populates = 'asset')

    # indexing
    __table_args__ = (
        Index('ix_asset_project_id', asset_project_id),
    )
