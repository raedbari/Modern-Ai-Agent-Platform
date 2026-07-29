"""Database utility functions for common operations."""

import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.security import hash_api_key
from backend.app.db.models import Agent, ApiKey, Conversation, Tenant


async def verify_agent_belongs_to_tenant(
    db: AsyncSession, agent_id: str, tenant_id: str
) -> Agent | None:
    """
    Verify that an agent belongs to a specific tenant.
    
    This is critical for multi-tenant security - prevents cross-tenant access.
    
    Args:
        db: Database session
        agent_id: The agent ID to check
        tenant_id: The tenant ID that should own the agent
        
    Returns:
        The Agent if it belongs to the tenant and is active, None otherwise
    """
    result = await db.execute(
        select(Agent)
        .where(Agent.id == agent_id)
        .where(Agent.tenant_id == tenant_id)
        .where(Agent.is_active == True)
    )
    return result.scalar_one_or_none()


async def verify_conversation_belongs_to_tenant(
    db: AsyncSession, conversation_id: str, tenant_id: str
) -> Conversation | None:
    """
    Verify that a conversation belongs to a specific tenant.
    
    This is critical for multi-tenant security - prevents cross-tenant access.
    
    Args:
        db: Database session
        conversation_id: The conversation ID to check
        tenant_id: The tenant ID that should own the conversation
        
    Returns:
        The Conversation if it belongs to the tenant, None otherwise
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.tenant_id == tenant_id)
        .where(Conversation.is_archived == False)
    )
    return result.scalar_one_or_none()


async def get_tenant_by_id(db: AsyncSession, tenant_id: str) -> Tenant | None:
    """
    Get a tenant by ID if it's active.
    
    Args:
        db: Database session
        tenant_id: The tenant ID
        
    Returns:
        The Tenant if found and active, None otherwise
    """
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id).where(Tenant.is_active == True)
    )
    return result.scalar_one_or_none()


def generate_api_key() -> str:
    """
    Generate a cryptographically secure API key.
    
    Format: maap_<32 random hex characters>
    Example: maap_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
    
    Returns:
        A new API key string
        
    Note:
        This key should be shown to the user ONCE and never stored in plain text.
    """
    random_part = secrets.token_hex(32)
    return f"maap_{random_part}"


async def create_api_key_for_tenant(
    db: AsyncSession,
    tenant_id: str,
    name: str,
    expires_at: datetime | None = None,
) -> tuple[ApiKey, str]:
    """
    Create a new API key for a tenant.
    
    Args:
        db: Database session
        tenant_id: The tenant ID
        name: Human-readable name for the key
        expires_at: Optional expiration datetime
        
    Returns:
        Tuple of (ApiKey model, plain_key_string)
        
    Note:
        The plain key is returned ONLY during creation.
        It must be shown to the user immediately and cannot be retrieved later.
    """
    # Generate plain key
    plain_key = generate_api_key()
    
    # Hash it for storage
    key_hash = hash_api_key(plain_key)
    
    # Create the database record
    api_key = ApiKey(
        tenant_id=tenant_id,
        key_hash=key_hash,
        name=name,
        is_active=True,
        expires_at=expires_at,
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    return api_key, plain_key


async def verify_agent_and_conversation_match(
    db: AsyncSession, agent_id: str, conversation_id: str, tenant_id: str
) -> bool:
    """
    Verify that an agent and conversation belong to the same tenant
    and that the conversation is using that agent.
    
    Args:
        db: Database session
        agent_id: The agent ID
        conversation_id: The conversation ID
        tenant_id: The tenant ID
        
    Returns:
        True if all relationships are valid, False otherwise
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.tenant_id == tenant_id)
        .where(Conversation.agent_id == agent_id)
        .where(Conversation.is_archived == False)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        return False
    
    # Also verify the agent belongs to this tenant
    agent = await verify_agent_belongs_to_tenant(db, agent_id, tenant_id)
    return agent is not None


def generate_conversation_id() -> str:
    """
    Generate a unique conversation ID.
    
    Format: conv_<16 random hex characters>
    
    Returns:
        A new conversation ID
    """
    return f"conv_{secrets.token_hex(16)}"


def generate_request_id() -> str:
    """
    Generate a unique request ID for tracing.
    
    Format: req_<16 random hex characters>
    
    Returns:
        A new request ID
    """
    return f"req_{secrets.token_hex(16)}"
