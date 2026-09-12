"""Phase 9 human-handoff migration.

The project's 0001 migration intentionally uses Base.metadata.create_all(), so
its schema already contains the Phase 9 handoff models that are part of the
metadata.  Recreating those tables here would make a fresh `alembic upgrade
head` fail with DuplicateTableError.  This revision is therefore a schema
compatibility marker; future handoff schema changes must use explicit ALTER
operations in a later revision.
"""

from alembic import op

revision = '0003_human_handoff'
down_revision = '0002_call_intelligence'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
