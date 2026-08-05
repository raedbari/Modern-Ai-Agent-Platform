"""Prevent concurrent active ingestion jobs per document.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-08-04 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow only one pending or processing job per document."""

    duplicate = op.get_bind().execute(
        sa.text(
            """
            SELECT tenant_id, document_id, COUNT(*) AS active_count
            FROM ingestion_jobs
            WHERE status IN ('pending', 'processing')
            GROUP BY tenant_id, document_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()

    if duplicate is not None:
        raise RuntimeError(
            "Cannot add the active ingestion-job guard while "
            "duplicate pending or processing jobs exist."
        )

    op.create_index(
        "uq_ingestion_jobs_active_document",
        "ingestion_jobs",
        ["tenant_id", "document_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('pending', 'processing')"
        ),
    )


def downgrade() -> None:
    """Remove the active-document ingestion guard."""

    op.drop_index(
        "uq_ingestion_jobs_active_document",
        table_name="ingestion_jobs",
    )
