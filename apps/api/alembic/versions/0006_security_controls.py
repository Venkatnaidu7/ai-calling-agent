"""Add security-control metadata indexes."""
from alembic import op

revision='0006_security_controls'
down_revision='0005_billing_events'
branch_labels=None
depends_on=None

def upgrade():
    # Security controls are application-level in this release; existing
    # tenant-scoped ApiKey/AuditLog tables require no schema mutation.
    pass

def downgrade():
    pass
