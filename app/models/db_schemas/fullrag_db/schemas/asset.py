from .fullrag_base import SQLAlchemyBase

from sqlalchemy import Column, Integer, String, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy.orm import relationship

class Asset(SQLAlchemyBase):
    # table name
    __tablename__ = 'assets'

    # columns
    asset_id   = Column(Integer, primary_key = True, autoincrement = True)
    asset_name = Column(String, nullable = False)
    asset_type = Column(String, nullable = False, default = 'file')
    asset_metadata = Column(
        JSONB, # binary json: fast in reading [data alreay in binary]
        nullable = True
    )


    user_id = Column(Integer, ForeignKey('users.user_id', ondelete = 'CASCADE'), nullable = False)


    # linking
    user   = relationship("User", back_populates = 'assets')
    chunks = relationship('DataChunk', back_populates = 'asset')

    # indexing
    __table_args__ = (
        Index('ix_asset_user_id', user_id),
        UniqueConstraint('user_id', 'asset_name', name = 'uq_user_asset_name'),
    )
