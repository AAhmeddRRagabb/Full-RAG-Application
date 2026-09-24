
from .fullrag_base import SQLAlchemyBase

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

class Message(SQLAlchemyBase):
    __tablename__ = 'messages'


    # columns
    message_id = Column(Integer, primary_key = True, autoincrement = True)
    chat_id    = Column(Integer, ForeignKey('chats.chat_id', ondelete = 'CASCADE'), nullable = False)

    role = Column(String, nullable = False)
    content = Column(String, nullable = False)
    llm_resources = Column(  # resources where the LLM gets the answer
        JSONB, 
        nullable = True
    )

    created_at = Column(DateTime(timezone = True), server_default = func.now(), nullable = False)

    # linking
    chat = relationship("Chat", back_populates = 'messages')


    # indexing
    __table_args__ = (
        Index('ix_message_chat_id', chat_id),
    )
