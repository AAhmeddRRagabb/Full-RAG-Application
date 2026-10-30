"""Add step name to run steps.

Revision ID: c7e9f2a4b631
Revises: f4a1b5c8d2e0
"""

from alembic import op
import sqlalchemy as sa


revision = "c7e9f2a4b631"
down_revision = "f4a1b5c8d2e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("run_steps", sa.Column("step_name", sa.String(), nullable=False, server_default="unknown"))


def downgrade() -> None:
    op.drop_column("run_steps", "step_name")
