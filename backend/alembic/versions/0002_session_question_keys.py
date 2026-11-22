"""Record which questions each check-in asked.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Null for check-ins started before this column existed.
    op.add_column('sessions', sa.Column('question_keys', JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column('sessions', 'question_keys')
