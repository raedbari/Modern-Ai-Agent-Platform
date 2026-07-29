"""Database configuration and session management."""

from backend.app.db.base import Base
from backend.app.db.models import Agent, ApiKey, Conversation, Message, Tenant
from backend.app.db.session import get_db, init_db
from backend.app.db.utils import (
    create_api_key_for_tenant,
    generate_api_key,
    generate_conversation_id,
    generate_request_id,
    get_tenant_by_id,
    verify_agent_and_conversation_match,
    verify_agent_belongs_to_tenant,
    verify_conversation_belongs_to_tenant,
)

__all__ = [
    "Base",
    "get_db",
    "init_db",
    "Tenant",
    "ApiKey",
    "Agent",
    "Conversation",
    "Message",
    "verify_agent_belongs_to_tenant",
    "verify_conversation_belongs_to_tenant",
    "verify_agent_and_conversation_match",
    "get_tenant_by_id",
    "generate_api_key",
    "create_api_key_for_tenant",
    "generate_conversation_id",
    "generate_request_id",
]
