"""Add journal_entries.source ('chat' | 'solo'), which the model uses but no migration created.

Some existing databases already have this column (added outside migrations), so it
is added only if missing.

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS source VARCHAR(20)")


def downgrade() -> None:
    op.execute("ALTER TABLE journal_entries DROP COLUMN IF EXISTS source")
