"""add pgvector knowledge storage

Revision ID: 8d2f4a7c91b6
Revises: 53ab55304372
Create Date: 2026-07-30 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import VECTOR
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8d2f4a7c91b6"
down_revision: Union[str, Sequence[str], None] = "53ab55304372"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tenant-safe knowledge, document, and vector chunk storage."""

    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"
    if is_postgresql:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "description",
            sa.Text(),
            server_default="",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_knowledge_bases_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_knowledge_bases_tenant_id_id",
        ),
    )
    op.create_index(
        "ix_knowledge_bases_tenant_status",
        "knowledge_bases",
        ["tenant_id", "status"],
        unique=False,
    )

    op.create_table(
        "agent_knowledge_bases",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column(
            "knowledge_base_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            name="fk_agent_knowledge_bases_tenant_agent",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id"],
            ["knowledge_bases.tenant_id", "knowledge_bases.id"],
            name="fk_agent_knowledge_bases_tenant_kb",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "tenant_id",
            "agent_id",
            "knowledge_base_id",
            name="pk_agent_knowledge_bases",
        ),
    )
    op.create_index(
        "ix_agent_knowledge_bases_tenant_kb",
        "agent_knowledge_bases",
        ["tenant_id", "knowledge_base_id"],
        unique=False,
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column(
            "knowledge_base_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("agent_id", sa.String(length=128), nullable=True),
        sa.Column("source_name", sa.String(length=512), nullable=False),
        sa.Column(
            "original_filename",
            sa.String(length=512),
            nullable=False,
        ),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("failure_reason", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "file_size_bytes >= 0",
            name="ck_documents_file_size",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            name="fk_documents_tenant_agent",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id"],
            ["knowledge_bases.tenant_id", "knowledge_bases.id"],
            name="fk_documents_tenant_kb",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_documents_tenant_id_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "knowledge_base_id",
            "id",
            name="uq_documents_tenant_kb_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "knowledge_base_id",
            "content_hash",
            name="uq_documents_tenant_kb_content_hash",
        ),
    )
    op.create_index(
        "ix_documents_tenant_kb_status",
        "documents",
        ["tenant_id", "knowledge_base_id", "status"],
        unique=False,
    )

    embedding_type = VECTOR(1024) if is_postgresql else sa.JSON()
    op.create_table(
        "chunks",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column(
            "knowledge_base_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("source_name", sa.String(length=512), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", embedding_type, nullable=False),
        sa.CheckConstraint(
            "chunk_index >= 0",
            name="ck_chunks_chunk_index",
        ),
        sa.CheckConstraint(
            "page_number >= 0",
            name="ck_chunks_page_number",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            name="fk_chunks_tenant_agent",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id"],
            ["knowledge_bases.tenant_id", "knowledge_bases.id"],
            name="fk_chunks_tenant_kb",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id", "document_id"],
            [
                "documents.tenant_id",
                "documents.knowledge_base_id",
                "documents.id",
            ],
            name="fk_chunks_tenant_kb_document",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "document_id",
            "chunk_index",
            name="uq_chunks_tenant_document_index",
        ),
    )
    op.create_index(
        "ix_chunks_tenant_agent_kb",
        "chunks",
        ["tenant_id", "agent_id", "knowledge_base_id"],
        unique=False,
    )
    op.create_index(
        "ix_chunks_tenant_document",
        "chunks",
        ["tenant_id", "document_id"],
        unique=False,
    )
    if is_postgresql:
        op.create_index(
            "ix_chunks_embedding_hnsw_cosine",
            "chunks",
            ["embedding"],
            unique=False,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        )


def downgrade() -> None:
    """Remove knowledge storage while leaving the shared vector extension."""

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index(
            "ix_chunks_embedding_hnsw_cosine",
            table_name="chunks",
            postgresql_using="hnsw",
        )
    op.drop_index("ix_chunks_tenant_document", table_name="chunks")
    op.drop_index("ix_chunks_tenant_agent_kb", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index(
        "ix_documents_tenant_kb_status",
        table_name="documents",
    )
    op.drop_table("documents")
    op.drop_index(
        "ix_agent_knowledge_bases_tenant_kb",
        table_name="agent_knowledge_bases",
    )
    op.drop_table("agent_knowledge_bases")
    op.drop_index(
        "ix_knowledge_bases_tenant_status",
        table_name="knowledge_bases",
    )
    op.drop_table("knowledge_bases")
