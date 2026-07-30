"""Database models for the multi-tenant AI Agent Platform."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import VECTOR

from backend.app.db.base import Base

EMBEDDING_DIMENSION = 1024


class Tenant(Base):
    """A tenant using the platform."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    api_keys: Mapped[list[ApiKey]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    agents: Mapped[list[Agent]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ApiKey(Base):
    """API key metadata without storing the raw secret."""

    __tablename__ = "api_keys"
    __table_args__ = (
        Index(
            "ix_api_keys_tenant_active",
            "tenant_id",
            "is_active",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    key_digest: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    tenant: Mapped[Tenant] = relationship(back_populates="api_keys")


class Agent(Base):
    """An AI agent belonging to one tenant."""

    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_agents_tenant_id_id",
        ),
        CheckConstraint(
            "knowledge_mode IN ('required', 'preferred', 'disabled')",
            name="ck_agents_knowledge_mode",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text)
    knowledge_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="preferred",
        server_default="preferred",
    )
    fallback_message: Mapped[str | None] = mapped_column(Text)
    handoff_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="agents")
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Conversation(Base):
    """A conversation belonging to one tenant and agent."""

    __tablename__ = "conversations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            ondelete="CASCADE",
            name="fk_conversations_tenant_agent",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_conversations_tenant_id_id",
        ),
        Index(
            "ix_conversations_tenant_agent",
            "tenant_id",
            "agent_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    user_identifier: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    agent: Mapped[Agent] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )


class Message(Base):
    """A message belonging to a tenant's conversation."""

    __tablename__ = "messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "conversation_id"],
            ["conversations.tenant_id", "conversations.id"],
            ondelete="CASCADE",
            name="fk_messages_tenant_conversation",
        ),
        CheckConstraint(
            "role IN ('system', 'user', 'assistant', 'tool')",
            name="ck_messages_role",
        ),
        Index(
            "ix_messages_tenant_conversation",
            "tenant_id",
            "conversation_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    conversation: Mapped[Conversation] = relationship(
        back_populates="messages"
    )


class KnowledgeBaseModel(Base):
    """A tenant-owned collection of documents used for retrieval."""

    __tablename__ = "knowledge_bases"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_knowledge_bases_tenant_id_id",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_knowledge_bases_status",
        ),
        Index(
            "ix_knowledge_bases_tenant_status",
            "tenant_id",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AgentKnowledgeBase(Base):
    """Tenant-safe many-to-many assignment between agents and knowledge bases."""

    __tablename__ = "agent_knowledge_bases"
    __table_args__ = (
        PrimaryKeyConstraint(
            "tenant_id",
            "agent_id",
            "knowledge_base_id",
            name="pk_agent_knowledge_bases",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            ondelete="CASCADE",
            name="fk_agent_knowledge_bases_tenant_agent",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id"],
            ["knowledge_bases.tenant_id", "knowledge_bases.id"],
            ondelete="CASCADE",
            name="fk_agent_knowledge_bases_tenant_kb",
        ),
        Index(
            "ix_agent_knowledge_bases_tenant_kb",
            "tenant_id",
            "knowledge_base_id",
        ),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    knowledge_base_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentModel(Base):
    """Persistent document lifecycle metadata."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_documents_tenant_id_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "knowledge_base_id",
            "id",
            name="uq_documents_tenant_kb_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "knowledge_base_id",
            "content_hash",
            name="uq_documents_tenant_kb_content_hash",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id"],
            ["knowledge_bases.tenant_id", "knowledge_bases.id"],
            ondelete="CASCADE",
            name="fk_documents_tenant_kb",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            name="fk_documents_tenant_agent",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name="ck_documents_status",
        ),
        CheckConstraint(
            "file_size_bytes >= 0",
            name="ck_documents_file_size",
        ),
        Index(
            "ix_documents_tenant_kb_status",
            "tenant_id",
            "knowledge_base_id",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    agent_id: Mapped[str | None] = mapped_column(String(128))
    source_name: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ChunkModel(Base):
    """A tenant- and agent-scoped text chunk with a pgvector embedding."""

    __tablename__ = "chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            ondelete="CASCADE",
            name="fk_chunks_tenant_agent",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id"],
            ["knowledge_bases.tenant_id", "knowledge_bases.id"],
            ondelete="CASCADE",
            name="fk_chunks_tenant_kb",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id", "document_id"],
            [
                "documents.tenant_id",
                "documents.knowledge_base_id",
                "documents.id",
            ],
            ondelete="CASCADE",
            name="fk_chunks_tenant_kb_document",
        ),
        UniqueConstraint(
            "tenant_id",
            "document_id",
            "chunk_index",
            name="uq_chunks_tenant_document_index",
        ),
        CheckConstraint(
            "page_number >= 0",
            name="ck_chunks_page_number",
        ),
        CheckConstraint(
            "chunk_index >= 0",
            name="ck_chunks_chunk_index",
        ),
        Index(
            "ix_chunks_tenant_agent_kb",
            "tenant_id",
            "agent_id",
            "knowledge_base_id",
        ),
        Index(
            "ix_chunks_tenant_document",
            "tenant_id",
            "document_id",
        ),
        Index(
            "ix_chunks_embedding_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    knowledge_base_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_name: Mapped[str] = mapped_column(String(512), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        VECTOR(EMBEDDING_DIMENSION).with_variant(JSON, "sqlite"),
        nullable=False,
    )
