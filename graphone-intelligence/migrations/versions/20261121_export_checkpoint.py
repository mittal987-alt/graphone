"""Add Google Sheets export checkpoints.

Revision ID: 20261121_export
Revises: 20261121_initial
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20261121_export"
down_revision = "20261121_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("export_checkpoints"):
        op.create_table(
            "export_checkpoints",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tab_name", sa.String(length=100), nullable=False),
            sa.Column("last_record_id", sa.String(length=36), nullable=True),
            sa.Column("last_row_count", sa.Integer(), nullable=False),
            sa.Column("last_exported_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("raw_metadata", sa.JSON(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tab_name", name="uq_export_checkpoint_tab"),
        )
    existing_indexes = (
        {index["name"] for index in inspector.get_indexes("export_checkpoints")}
        if inspector.has_table("export_checkpoints")
        else set()
    )
    if "ix_export_checkpoints_tab_name" not in existing_indexes:
        op.create_index(
            "ix_export_checkpoints_tab_name",
            "export_checkpoints",
            ["tab_name"],
            unique=False,
        )
    if "ix_export_checkpoints_status" not in existing_indexes:
        op.create_index(
            "ix_export_checkpoints_status",
            "export_checkpoints",
            ["status"],
            unique=False,
        )


def downgrade() -> None:
    raise RuntimeError(
        "Downgrade is disabled: dropping export checkpoints requires explicit approval"
    )
