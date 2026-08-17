"""complete knowledge versioning and governance invariants

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""

from alembic import op
import sqlalchemy as sa

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("version_family_id", sa.String(128), nullable=True))
    op.add_column("documents", sa.Column("predecessor_id", sa.String(128), nullable=True))
    op.execute("UPDATE documents SET version_family_id = id WHERE version_family_id IS NULL")
    op.create_foreign_key(
        "fk_documents_predecessor", "documents", "documents",
        ["predecessor_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index(
        "ix_documents_tenant_kb_family_version", "documents",
        ["tenant_id", "knowledge_base_id", "version_family_id", "version_number"],
        unique=True,
    )
    op.drop_index("uq_documents_active_per_tenant_kb_filename", table_name="documents")
    op.create_index(
        "uq_documents_active_per_tenant_kb_family", "documents",
        ["tenant_id", "knowledge_base_id", "version_family_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('ready', 'active')"),
    )
    op.create_check_constraint(
        "ck_knowledge_bases_classification", "knowledge_bases",
        "classification IN ('public', 'internal', 'restricted')",
    )
    op.alter_column("chunks", "agent_id", nullable=True)


def downgrade() -> None:
    op.alter_column("chunks", "agent_id", nullable=False)
    op.drop_constraint("ck_knowledge_bases_classification", "knowledge_bases", type_="check")
    op.drop_index("uq_documents_active_per_tenant_kb_family", table_name="documents")
    op.create_index(
        "uq_documents_active_per_tenant_kb_filename", "documents",
        ["tenant_id", "knowledge_base_id", "original_filename"], unique=False,
        postgresql_where=sa.text("status IN ('ready', 'active')"),
    )
    op.drop_index("ix_documents_tenant_kb_family_version", table_name="documents")
    op.drop_constraint("fk_documents_predecessor", "documents", type_="foreignkey")
    op.drop_column("documents", "predecessor_id")
    op.drop_column("documents", "version_family_id")
