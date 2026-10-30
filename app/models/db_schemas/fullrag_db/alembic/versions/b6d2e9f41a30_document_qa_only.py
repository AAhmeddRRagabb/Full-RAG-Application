"""Remove chat and run tables for document Q&A.

Revision ID: b6d2e9f41a30
Revises: 05fcd97efa67
"""

from alembic import op


revision = "b6d2e9f41a30"
down_revision = "05fcd97efa67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("run_steps")
    op.drop_table("runs")
    op.drop_table("messages")
    op.drop_table("chats")


def downgrade() -> None:
    raise NotImplementedError("Removed chat history cannot be restored by this migration")
