from alembic import op
revision='0001';down_revision=None;branch_labels=None;depends_on=None
def upgrade():
    from app.db.base import Base
    import app.models
    Base.metadata.create_all(bind=op.get_bind())
def downgrade():
    from app.db.base import Base
    Base.metadata.drop_all(bind=op.get_bind())
