"""Soft delete for check-ins that carry safety flags.

When a patient deletes a check-in with a safety flag, it is hidden from the patient but
kept (with its answers and safety flags) so the clinician still sees what was reported.

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('sessions', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('sessions', 'deleted_at')
