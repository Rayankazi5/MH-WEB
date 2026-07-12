"""Initial schema — all 10 tables

Revision ID: 0001
Revises:
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.Text, nullable=False, unique=True),
        sa.Column('password_hash', sa.Text, nullable=False),
        sa.Column('role', sa.String, nullable=False),
        sa.Column('full_name', sa.Text, nullable=False),
        sa.Column('timezone', sa.Text, nullable=False, server_default='UTC'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.CheckConstraint("role IN ('patient', 'clinician')", name='ck_users_role'),
    )
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'clinician_patient',
        sa.Column('clinician_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('linked_at', sa.DateTime(timezone=True)),
        sa.Column('active', sa.Boolean, server_default='true'),
    )

    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('device_type', sa.String(20)),
        sa.Column('abstained', sa.Boolean, server_default='false'),
        sa.Column('uncertainty_val', sa.Float),
    )
    op.create_index('ix_sessions_patient_id', 'sessions', ['patient_id'])

    op.create_table(
        'questionnaire_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_key', sa.String(50), nullable=False),
        sa.Column('question_type', sa.String(20), nullable=False),
        sa.Column('raw_value', postgresql.JSONB, nullable=False),
        sa.Column('normalised_val', sa.Float),
        sa.Column('response_time_ms', sa.Integer),
        sa.Column('answered_at', sa.DateTime(timezone=True)),
    )

    op.create_table(
        'journal_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE')),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('body_encrypted', sa.Text, nullable=False),
        sa.Column('keyword_vector', postgresql.JSONB),
        sa.Column('sentiment_score', sa.Float),
        sa.Column('word_count', sa.Integer),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )

    op.create_table(
        'domain_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('domain', sa.String(30), nullable=False),
        sa.Column('score', sa.Float, nullable=False),
        sa.Column('confidence', sa.Float),
        sa.Column('computed_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_domain_scores_patient_computed', 'domain_scores', ['patient_id', sa.text('computed_at DESC')])

    op.create_table(
        'narratives',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('week_start', sa.Date, nullable=False),
        sa.Column('bullets', postgresql.JSONB, nullable=False),
        sa.Column('raw_llm_output', sa.Text),
        sa.Column('generated_at', sa.DateTime(timezone=True)),
    )

    op.create_table(
        'dissonance_flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('flag_type', sa.String(50), nullable=False),
        sa.Column('self_report_val', sa.Text),
        sa.Column('signal_val', sa.Text),
        sa.Column('severity', sa.String(10)),
        sa.Column('resolved', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint("severity IN ('low','medium','high')", name='ck_flags_severity'),
    )

    op.create_table(
        'consent_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('consented_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.Text, nullable=False, server_default='1.0'),
        sa.Column('ip_address', sa.Text),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
    )

    op.create_table(
        'push_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.Text, nullable=False),
        sa.Column('platform', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.UniqueConstraint('user_id', 'token', name='uq_push_token_user_token'),
    )


def downgrade() -> None:
    op.drop_table('push_tokens')
    op.drop_table('consent_records')
    op.drop_table('dissonance_flags')
    op.drop_table('narratives')
    op.drop_index('ix_domain_scores_patient_computed', 'domain_scores')
    op.drop_table('domain_scores')
    op.drop_table('journal_entries')
    op.drop_table('questionnaire_responses')
    op.drop_index('ix_sessions_patient_id', 'sessions')
    op.drop_table('sessions')
    op.drop_table('clinician_patient')
    op.drop_index('ix_users_email', 'users')
    op.drop_table('users')
