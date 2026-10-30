"""Keep only run step inputs, outputs, duration, and status.

Revision ID: f4a1b5c8d2e0
Revises: 2d0c0254e81e
"""

from alembic import op
import sqlalchemy as sa


revision = "f4a1b5c8d2e0"
down_revision = "2d0c0254e81e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("run_steps", sa.Column("status", sa.String(), nullable=False, server_default="success"))
    op.alter_column("run_steps", "duration_s", new_column_name="duration")
    op.drop_column("run_steps", "step_order")
    op.drop_column("run_steps", "step_name")
    op.drop_column("run_steps", "step_reason")
    op.drop_column("run_steps", "created_at")


def downgrade() -> None:
    op.add_column("run_steps", sa.Column("step_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("run_steps", sa.Column("step_name", sa.String(), nullable=False, server_default="unknown"))
    op.add_column("run_steps", sa.Column("step_reason", sa.String(), nullable=True))
    op.add_column("run_steps", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.drop_column("run_steps", "status")
    op.alter_column("run_steps", "duration", new_column_name="duration_s")
