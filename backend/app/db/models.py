"""Database models for multi-tenant AI Agent Platform."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


def utc_now() -> datetime:
    """Return current UTC time for database timestamps."""
    return datetime.now(timezone.utc)


class Client(Base):
    """Represents a tenant/client in the multi-tenant system."""

    __tablename__ = "clients"

    id = Column(String(128), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    api_keys = relationship("ApiKey", back_populates="client", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="client", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="client", cascade="all, delete-orphan")


class Agent(Base):
    """Represents an AI agent belonging to a specific client."""

    __tablename__ = "agents"

    id = Column(String(128), primary_key=True, index=True)
    client_id = Column(String(128), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    system_prompt = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    client = relationship("Client", back_populates="agents")
    conversations = relationship("Conversation", back_populates="agent", cascade="all, delete-orphan")


class ApiKey(Base):
    """Stores hashed API keys for authentication. Never stores plain keys."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(String(128), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=True)  # Optional friendly name
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="api_keys")


class Conversation(Base):
    """Represents a conversation thread between a user and an agent."""

    __tablename__ = "conversations"

    id = Column(String(128), primary_key=True, index=True)
    client_id = Column(String(128), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(128), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_identifier = Column(String(255), nullable=True)  # Optional external user ID
    metadata = Column(Text, nullable=True)  # JSON metadata
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    client = relationship("Client", back_populates="conversations")
    agent = relationship("Agent", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    """Represents a single message in a conversation."""

    __tablename__ = "messages"

    id = Column(String(128), primary_key=True, index=True)
    conversation_id = Column(String(128), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
