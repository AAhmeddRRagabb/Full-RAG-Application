"""Add Chat Settings

Revision ID: 9f2a4f0d8c31
Revises: b2cc3699a936
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '9f2a4f0d8c31'
down_revision: Union[str, Sequence[str], None] = 'b2cc3699a936'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chats', sa.Column('chat_settings', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('chats', 'chat_settings')
