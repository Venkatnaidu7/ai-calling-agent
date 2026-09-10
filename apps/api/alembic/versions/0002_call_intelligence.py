from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002_call_intelligence'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'call_intelligence_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calls.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='QUEUED'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('call_id', name='uq_call_intelligence_job_call'),
    )
    op.create_index('ix_call_intelligence_jobs_tenant_id', 'call_intelligence_jobs', ['tenant_id'])
    op.create_index('ix_call_intelligence_jobs_status', 'call_intelligence_jobs', ['status'])
    op.create_table(
        'call_action_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calls.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('owner', sa.String(length=100), nullable=True),
        sa.Column('due_date', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='OPEN'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('call_id', 'description', name='uq_call_action_item'),
    )
    op.create_index('ix_call_action_items_tenant_id', 'call_action_items', ['tenant_id'])


def downgrade():
    op.drop_index('ix_call_action_items_tenant_id', table_name='call_action_items')
    op.drop_table('call_action_items')
    op.drop_index('ix_call_intelligence_jobs_status', table_name='call_intelligence_jobs')
    op.drop_index('ix_call_intelligence_jobs_tenant_id', table_name='call_intelligence_jobs')
    op.drop_table('call_intelligence_jobs')
