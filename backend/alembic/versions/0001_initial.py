"""Initial HawkerCredit schema."""
from alembic import op
from app.models.schema import Base
from app.db.database import engine

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    Base.metadata.create_all(bind=engine)

def downgrade():
    Base.metadata.drop_all(bind=engine)
