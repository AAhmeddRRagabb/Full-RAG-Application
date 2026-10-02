"""Add asset status and run logs

Revision ID: d92f4b87c1a0
Revises: 46eb8899dcd7
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d92f4b87c1a0"
down_revision: Union[str, Sequence[str], None] = "46eb8899dcd7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assets",
        sa.Column("asset_status", sa.String(), nullable = False, server_default = "ready"),
    )

    op.create_table(
        "runs",
        sa.Column("run_id", sa.Integer(), autoincrement = True, nullable = False),
        sa.Column("user_id", sa.Integer(), nullable = False),
        sa.Column("chat_id", sa.Integer(), nullable = True),
        sa.Column("user_query", sa.String(), nullable = False),
        sa.Column("response", sa.String(), nullable = True),
        sa.Column("status", sa.String(), nullable = False, server_default = "running"),
        sa.Column("error", sa.String(), nullable = True),
        sa.Column("run_metadata", postgresql.JSONB(astext_type = sa.Text()), nullable = True),
        sa.Column("started_at", sa.DateTime(timezone = True), server_default = sa.text("now()"), nullable = False),
        sa.Column("completed_at", sa.DateTime(timezone = True), nullable = True),
        sa.Column("duration_ms", sa.Float(), nullable = True),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.chat_id"], ondelete = "SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete = "CASCADE"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_run_user_id", "runs", ["user_id"])
    op.create_index("ix_run_chat_id", "runs", ["chat_id"])

    op.create_table(
        "run_steps",
        sa.Column("step_id", sa.Integer(), autoincrement = True, nullable = False),
        sa.Column("run_id", sa.Integer(), nullable = False),
        sa.Column("step_order", sa.Integer(), nullable = False),
        sa.Column("step_name", sa.String(), nullable = False),
        sa.Column("step_input", postgresql.JSONB(astext_type = sa.Text()), nullable = True),
        sa.Column("step_output", postgresql.JSONB(astext_type = sa.Text()), nullable = True),
        sa.Column("duration_ms", sa.Float(), nullable = True),
        sa.Column("created_at", sa.DateTime(timezone = True), server_default = sa.text("now()"), nullable = False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.run_id"], ondelete = "CASCADE"),
        sa.PrimaryKeyConstraint("step_id"),
    )
    op.create_index("ix_run_step_run_id", "run_steps", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_run_step_run_id", table_name = "run_steps")
    op.drop_table("run_steps")
    op.drop_index("ix_run_chat_id", table_name = "runs")
    op.drop_index("ix_run_user_id", table_name = "runs")
    op.drop_table("runs")
    op.drop_column("assets", "asset_status")
