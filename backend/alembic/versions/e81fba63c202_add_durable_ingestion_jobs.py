"""add durable ingestion jobs

Revision ID: e81fba63c202
Revises: d2e7c9a45130
Create Date: 2026-07-30 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e81fba63c202"
down_revision: Union[str, Sequence[str], None] = "d2e7c9a45130"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the PostgreSQL-backed ingestion work queue."""

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column(
            "knowledge_base_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "max_attempts",
            sa.Integer(),
            server_default="3",
            nullable=False,
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=255), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed')",
            name="ck_ingestion_jobs_status",
        ),
        sa.CheckConstraint(
            "attempts >= 0 AND max_attempts > 0",
            name="ck_ingestion_jobs_attempts",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            name="fk_ingestion_jobs_tenant_agent",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id", "document_id"],
            [
                "documents.tenant_id",
                "documents.knowledge_base_id",
                "documents.id",
            ],
            name="fk_ingestion_jobs_tenant_kb_document",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_jobs_claim",
        "ingestion_jobs",
        ["status", "available_at", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ingestion_jobs_tenant_agent",
        "ingestion_jobs",
        ["tenant_id", "agent_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove durable ingestion jobs."""

    op.drop_index(
        "ix_ingestion_jobs_tenant_agent",
        table_name="ingestion_jobs",
    )
    op.drop_index(
        "ix_ingestion_jobs_claim",
        table_name="ingestion_jobs",
    )
    op.drop_table("ingestion_jobs")
