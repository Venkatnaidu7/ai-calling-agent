"""Add Stripe billing event idempotency records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005_billing_events'
down_revision = '0004_call_handoffs'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'billing_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('stripe_event_id', sa.String(255), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('stripe_event_id', name='uq_billing_events_stripe_event_id'),
    )
    op.create_index('ix_billing_events_stripe_event_id', 'billing_events', ['stripe_event_id'], unique=True)

def downgrade():
    op.drop_index('ix_billing_events_stripe_event_id', table_name='billing_events')
    op.drop_table('billing_events')
