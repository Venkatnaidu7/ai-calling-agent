from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision='0004_call_handoffs'
down_revision='0003_human_handoff'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('call_handoffs',
        sa.Column('id',postgresql.UUID(as_uuid=True),primary_key=True,nullable=False),
        sa.Column('tenant_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('tenants.id',ondelete='CASCADE'),nullable=False),
        sa.Column('call_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('calls.id',ondelete='CASCADE'),nullable=False),
        sa.Column('destination_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('transfer_destinations.id'),nullable=True),
        sa.Column('destination_phone',sa.String(32),nullable=False),
        sa.Column('provider',sa.String(30),nullable=False),
        sa.Column('status',sa.String(30),nullable=False,server_default='REQUESTED'),
        sa.Column('reason',sa.Text(),nullable=True),
        sa.Column('failure_reason',sa.Text(),nullable=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('call_id',name='uq_call_handoff_call'))
    op.create_index('ix_call_handoffs_tenant_id','call_handoffs',['tenant_id'])
    op.create_index('ix_call_handoffs_status','call_handoffs',['status'])

def downgrade():
    op.drop_index('ix_call_handoffs_status',table_name='call_handoffs')
    op.drop_index('ix_call_handoffs_tenant_id',table_name='call_handoffs')
    op.drop_table('call_handoffs')
