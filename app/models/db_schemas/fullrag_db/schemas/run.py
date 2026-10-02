from .fullrag_base import SQLAlchemyBase

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship


class Run(SQLAlchemyBase):
    __tablename__ = "runs"

    run_id = Column(Integer, primary_key = True, autoincrement = True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete = "CASCADE"), nullable = False)
    chat_id = Column(Integer, ForeignKey("chats.chat_id", ondelete = "SET NULL"), nullable = True)

    user_query = Column(String, nullable = False)
    response = Column(String, nullable = True)
    status = Column(String, nullable = False, default = "running")
    error = Column(String, nullable = True)
    run_metadata = Column(JSONB, nullable = True)

    started_at = Column(DateTime(timezone = True), server_default = func.now(), nullable = False)
    completed_at = Column(DateTime(timezone = True), nullable = True)
    duration_s = Column(Float, nullable = True)

    steps = relationship("RunStep", back_populates = "run", cascade = "all, delete-orphan")

    __table_args__ = (
        Index("ix_run_user_id", user_id),
        Index("ix_run_chat_id", chat_id),
    )


class RunStep(SQLAlchemyBase):
    __tablename__ = "run_steps"

    step_id = Column(Integer, primary_key = True, autoincrement = True)
    run_id = Column(Integer, ForeignKey("runs.run_id", ondelete = "CASCADE"), nullable = False)

    step_order = Column(Integer, nullable = False)
    step_name = Column(String, nullable = False)
    step_input = Column(JSONB, nullable = True)
    step_output = Column(JSONB, nullable = True)

    duration_s = Column(Float, nullable = True)
    created_at = Column(DateTime(timezone = True), server_default = func.now(), nullable = False)

    run = relationship("Run", back_populates = "steps")

    __table_args__ = (
        Index("ix_run_step_run_id", run_id),
    )
