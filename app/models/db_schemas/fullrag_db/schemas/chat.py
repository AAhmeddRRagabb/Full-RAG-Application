from .fullrag_base import SQLAlchemyBase

from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

class Chat(SQLAlchemyBase):
    __tablename__ = 'chats'


    # columns
    chat_id   = Column(Integer, primary_key = True, autoincrement = True)
    chat_name = Column(String, nullable = False)

    user_id   = Column(Integer, ForeignKey('users.user_id', ondelete = 'CASCADE'), nullable = False)

    # linking
    user = relationship("User", back_populates = 'chats')
    messages = relationship("Message", back_populates = 'chat')

    # indexing
    __table_args__ = (
        Index('ix_chat_user_id', user_id),
    )
