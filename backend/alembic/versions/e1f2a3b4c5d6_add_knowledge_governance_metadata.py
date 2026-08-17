"""add knowledge governance metadata

Revision ID: e1f2a3b4c5d6
Revises: b13c7a9e42f6
Create Date: 2025-01-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "b13c7a9e42f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add governance metadata columns to documents and knowledge_bases."""

    # -------------------------------------------------------------------------
    # documents: version_number
    # -------------------------------------------------------------------------
    op.add_column(
        "documents",
        sa.Column(
            "version_number",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )

    # -------------------------------------------------------------------------
    # documents: superseded_by_id (self-FK, nullable)
    # -------------------------------------------------------------------------
    op.add_column(
        "documents",
        sa.Column(
            "superseded_by_id",
            sa.String(length=128),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_documents_superseded_by",
        "documents",
        "documents",
        ["superseded_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # -------------------------------------------------------------------------
    # documents: created_by (nullable, stores user/admin identifier string)
    # -------------------------------------------------------------------------
    op.add_column(
        "documents",
        sa.Column(
            "created_by",
            sa.String(length=255),
            nullable=True,
        ),
    )

    # -------------------------------------------------------------------------
    # documents: expand the status check constraint to include governance
    # lifecycle states (active, superseded, archived)
    # -------------------------------------------------------------------------
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.create_check_constraint(
        "ck_documents_status",
        "documents",
        "status IN ('pending', 'processing', 'ready', 'failed', 'active', 'superseded', 'archived')",
    )

    # -------------------------------------------------------------------------
    # Transitional lookup index. Filename is not a version-family key and
    # existing installations may legitimately contain duplicate filenames.
    # -------------------------------------------------------------------------
    op.create_index(
        "uq_documents_active_per_tenant_kb_filename",
        "documents",
        ["tenant_id", "knowledge_base_id", "original_filename"],
        unique=False,
        postgresql_where=sa.text("status IN ('ready', 'active')"),
    )

    # -------------------------------------------------------------------------
    # knowledge_bases: classification
    # -------------------------------------------------------------------------
    op.add_column(
        "knowledge_bases",
        sa.Column(
            "classification",
            sa.String(length=32),
            nullable=False,
            server_default="internal",
        ),
    )


def downgrade() -> None:
    """Remove governance metadata columns from documents and knowledge_bases."""

    # knowledge_bases
    op.drop_column("knowledge_bases", "classification")

    # documents — partial index
    op.drop_index(
        "uq_documents_active_per_tenant_kb_filename",
        table_name="documents",
    )

    # documents — restore original (narrower) status check constraint
    op.drop_constraint("ck_documents_status", "documents", type_="check")
    op.create_check_constraint(
        "ck_documents_status",
        "documents",
        "status IN ('pending', 'processing', 'ready', 'failed')",
    )

    # documents — governance columns
    op.drop_constraint(
        "fk_documents_superseded_by",
        "documents",
        type_="foreignkey",
    )
    op.drop_column("documents", "superseded_by_id")
    op.drop_column("documents", "created_by")
    op.drop_column("documents", "version_number")
