"""Phase 9 handoff migration compatibility marker.

0001_initial.py builds the schema from Base.metadata.create_all(), and the
Phase 9 CallHandoff model is already part of that metadata. Creating the table
again here would fail on every fresh database with DuplicateTableError.

Keep this revision as a versioned compatibility marker. Future handoff schema
changes must use explicit ALTER operations in a later revision.
"""

revision = '0004_call_handoffs'
down_revision = '0003_human_handoff'
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
