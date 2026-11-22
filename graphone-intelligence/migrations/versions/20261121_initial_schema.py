"""Create the complete GraphOne database schema.

Revision ID: 20261121_initial
Revises: None
"""

from alembic import op

from src.storage.models import Base

revision = "20261121_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    raise RuntimeError(
        "Downgrade is disabled: dropping GraphOne tables requires explicit approval"
    )
