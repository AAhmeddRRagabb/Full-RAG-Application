from .fullrag_base import SQLAlchemyBase

from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.orm import relationship


class DataChunk(SQLAlchemyBase):
    # table name
    __tablename__ = 'chunks'

    # columns
    chunk_id   = Column(Integer, primary_key = True, autoincrement = True)

    chunk_text  = Column(String, nullable = False)
    chunk_metadata = Column(
        JSONB, # binary json: fast in reading [data alreay in binary]
        nullable = True
    )

    user_id  = Column(Integer, ForeignKey('users.user_id', ondelete = 'CASCADE'), nullable = False)
    asset_id = Column(Integer, ForeignKey('assets.asset_id', ondelete = 'CASCADE'), nullable = False)


    user  = relationship("User", back_populates = 'chunks')
    asset = relationship("Asset", back_populates = 'chunks')


    # indexing
    __table_args__ = (
        Index('ix_chunk_user_id', user_id),
        Index('ix_chunk_asset_id',  asset_id),
    )


