
from .fullrag_base import SQLAlchemyBase
import uuid

from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID

class Chat(SQLAlchemyBase):
    __tablename__ = 'chats'


    # columns
    chat_id   = Column(Integer, primary_key = True, autoincrement = True)
    chat_uuid = Column(UUID(as_uuid = True), unique = True, default = uuid.uuid4, nullable = False)
    chat_name = Column(String, nullable = False)
    chat_settings = Column(JSONB, nullable = True)
    user_id   = Column(Integer, ForeignKey('users.user_id', ondelete = 'CASCADE'), nullable = False)

    # linking
    user = relationship("User", back_populates = 'chats')
    messages = relationship("Message", back_populates = 'chat')

    # indexing
    __table_args__ = (
        Index('ix_chat_user_id', user_id),
    )
