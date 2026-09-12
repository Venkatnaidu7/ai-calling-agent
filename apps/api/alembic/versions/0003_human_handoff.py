from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision='0003_human_handoff'
down_revision='0002_call_intelligence'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('human_agents',sa.Column('id',postgresql.UUID(as_uuid=True),primary_key=True),sa.Column('tenant_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('tenants.id'),nullable=False),sa.Column('name',sa.String(150),nullable=False),sa.Column('phone',sa.String(32),nullable=False),sa.Column('status',sa.String(20),nullable=False,server_default='OFFLINE'),sa.Column('priority',sa.Integer(),nullable=False,server_default='0'),sa.Column('department',sa.String(100)),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    op.create_table('routing_groups',sa.Column('id',postgresql.UUID(as_uuid=True),primary_key=True),sa.Column('tenant_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('tenants.id'),nullable=False),sa.Column('name',sa.String(150),nullable=False),sa.Column('strategy',sa.String(30),nullable=False,server_default='ROUND_ROBIN'),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    op.create_table('transfer_destinations',sa.Column('id',postgresql.UUID(as_uuid=True),primary_key=True),sa.Column('tenant_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('tenants.id'),nullable=False),sa.Column('name',sa.String(150),nullable=False),sa.Column('phone',sa.String(32),nullable=False),sa.Column('routing_group_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('routing_groups.id')),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))
    op.create_table('business_hours',sa.Column('id',postgresql.UUID(as_uuid=True),primary_key=True),sa.Column('tenant_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('tenants.id'),unique=True),sa.Column('timezone',sa.String(64),nullable=False,server_default='Asia/Kolkata'),sa.Column('hours',sa.JSON(),nullable=False,server_default='{}'),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False))


def downgrade():
    op.drop_table('business_hours'); op.drop_table('transfer_destinations'); op.drop_table('routing_groups'); op.drop_table('human_agents')
