"""Add retained source metadata to ingestion jobs.

Revision ID: c9d0e1f2a3b4
Revises: b7c8d9e0f1a2
Create Date: 2026-08-04 19:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Retain immutable source metadata for each ingestion attempt."""

    op.add_column(
        "ingestion_jobs",
        sa.Column("source_filename", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column("source_mime_type", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column("source_name", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    """Remove per-job source metadata."""

    op.drop_column("ingestion_jobs", "source_name")
    op.drop_column("ingestion_jobs", "source_mime_type")
    op.drop_column("ingestion_jobs", "source_filename")
