"""SQLAlchemy models for multi-tenant secure chat platform."""

from datetime import datetime
from typing import Literal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    """
    Represents a client organization in the multi-tenant system.
    
    All data is isolated by tenant_id to ensure complete separation.
    """

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    api_keys: Mapped[list["ApiKey"]] = relationship(
        "ApiKey", back_populates="tenant", cascade="all, delete-orphan"
    )
    agents: Mapped[list["Agent"]] = relationship(
        "Agent", back_populates="tenant", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id!r}, name={self.name!r}, active={self.is_active})>"


class ApiKey(Base, TimestampMixin):
    """
    Stores hashed API keys for authentication.
    
    Security rules:
    - Only the hash is stored, never the plain key
    - Plain key is shown ONCE during creation, never retrievable
    - Can be revoked but not deleted to maintain audit trail
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Human-readable key identifier"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_tenant_id", "tenant_id"),
        Index("ix_api_keys_key_hash", "key_hash"),
    )

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, tenant={self.tenant_id!r}, name={self.name!r})>"


class Agent(Base, TimestampMixin):
    """
    AI Agent configuration scoped to a specific tenant.
    
    Each tenant can have multiple agents with different purposes.
    Agents cannot be shared across tenants.
    """

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    system_prompt: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="agents")
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="agent", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_agents_tenant_id", "tenant_id"),
        UniqueConstraint("tenant_id", "name", name="uq_agents_tenant_name"),
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id!r}, tenant={self.tenant_id!r}, name={self.name!r})>"


class Conversation(Base, TimestampMixin):
    """
    A conversation thread between a user and an agent.
    
    Conversations are scoped to a tenant and must reference a valid agent
    belonging to the same tenant.
    """

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(500))
    user_id: Mapped[str | None] = mapped_column(
        String(64), comment="External user identifier from tenant's system"
    )
    metadata_json: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="conversations")
    agent: Mapped["Agent"] = relationship("Agent", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_conversations_tenant_id", "tenant_id"),
        Index("ix_conversations_agent_id", "agent_id"),
        Index("ix_conversations_user_id", "user_id"),
        Index("ix_conversations_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id!r}, tenant={self.tenant_id!r}, agent={self.agent_id!r})>"


class Message(Base, TimestampMixin):
    """
    Individual message within a conversation.
    
    Messages form the chat history and are strictly ordered by created_at.
    """

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Message role: system, user, or assistant",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Token usage tracking
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Generation metadata
    model: Mapped[str | None] = mapped_column(String(100))
    finish_reason: Mapped[str | None] = mapped_column(String(50))
    latency_ms: Mapped[float | None] = mapped_column(Integer)
    
    # Idempotency support
    request_id: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(255))

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_created_at", "created_at"),
        Index("ix_messages_idempotency_key", "idempotency_key"),
    )

    def __repr__(self) -> str:
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, conversation={self.conversation_id!r}, role={self.role!r}, content={preview!r})>"
