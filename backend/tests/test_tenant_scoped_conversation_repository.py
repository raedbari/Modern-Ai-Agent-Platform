"""Unit tests for tenant-scoped conversation repository."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Agent, Conversation, Tenant
from backend.app.infrastructure.database.tenant_repositories import (
    TenantScopedConversationRepository,
)
from backend.tests.conftest import async_session_maker


@pytest.fixture
async def seeded_session(async_session_maker):
    """Seed test data for conversation repository tests."""
    async with async_session_maker() as session:
        # Create tenants
        session.add_all([
            Tenant(id="tenant-a", name="Tenant A"),
            Tenant(id="tenant-b", name="Tenant B"),
        ])
        await session.flush()
        
        # Create agents
        session.add_all([
            Agent(id="agent-a1", tenant_id="tenant-a", name="Agent A1"),
            Agent(id="agent-a2", tenant_id="tenant-a", name="Agent A2"),
            Agent(id="agent-b1", tenant_id="tenant-b", name="Agent B1"),
        ])
        await session.flush()
        
        # Create conversations
        session.add_all([
            Conversation(id="conv-a1-1", agent_id="agent-a1"),
            Conversation(id="conv-a1-2", agent_id="agent-a1"),
            Conversation(id="conv-a2-1", agent_id="agent-a2"),
            Conversation(id="conv-b1-1", agent_id="agent-b1"),
        ])
        await session.commit()
    
    async with async_session_maker() as session:
        yield session


@pytest.mark.asyncio
async def test_list_by_agent_returns_only_tenant_conversations(
    seeded_session: AsyncSession,
) -> None:
    """Test list_by_agent filters by tenant_id."""
    repo = TenantScopedConversationRepository(seeded_session)
    
    # Tenant A lists conversations for agent-a1
    conversations = await repo.list_by_agent("agent-a1", "tenant-a")
    
    assert len(conversations) == 2
    assert {conv.id for conv in conversations} == {"conv-a1-1", "conv-a1-2"}


@pytest.mark.asyncio
async def test_list_by_agent_returns_empty_for_cross_tenant_agent(
    seeded_session: AsyncSession,
) -> None:
    """Test list_by_agent returns empty list for cross-tenant agent."""
    repo = TenantScopedConversationRepository(seeded_session)
    
    # Tenant A tries to list conversations for Tenant B's agent
    conversations = await repo.list_by_agent("agent-b1", "tenant-a")
    
    assert conversations == []


@pytest.mark.asyncio
async def test_list_by_agent_returns_empty_for_nonexistent_agent(
    seeded_session: AsyncSession,
) -> None:
    """Test list_by_agent returns empty list for nonexistent agent."""
    repo = TenantScopedConversationRepository(seeded_session)
    
    conversations = await repo.list_by_agent("nonexistent", "tenant-a")
    
    assert conversations == []


@pytest.mark.asyncio
async def test_get_by_id_returns_conversation_for_same_tenant(
    seeded_session: AsyncSession,
) -> None:
    """Test get_by_id returns conversation if agent belongs to tenant."""
    repo = TenantScopedConversationRepository(seeded_session)
    
    conversation = await repo.get_by_id("conv-a1-1", "tenant-a")
    
    assert conversation is not None
    assert conversation.id == "conv-a1-1"
    assert conversation.agent_id == "agent-a1"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_cross_tenant_conversation(
    seeded_session: AsyncSession,
) -> None:
    """Test get_by_id returns None for cross-tenant access."""
    repo = TenantScopedConversationRepository(seeded_session)
    
    # Tenant A tries to access Tenant B's conversation
    conversation = await repo.get_by_id("conv-b1-1", "tenant-a")
    
    assert conversation is None


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_nonexistent_conversation(
    seeded_session: AsyncSession,
) -> None:
    """Test get_by_id returns None for nonexistent conversation."""
    repo = TenantScopedConversationRepository(seeded_session)
    
    conversation = await repo.get_by_id("nonexistent", "tenant-a")
    
    assert conversation is None


@pytest.mark.asyncio
async def test_delete_removes_conversation_for_same_tenant(
    seeded_session: AsyncSession,
) -> None:
    """Test delete removes conversation if agent belongs to tenant."""
    repo = TenantScopedConversationRepository(seeded_session)
    
    deleted = await repo.delete("conv-a1-1", "tenant-a")
    
    assert deleted is True
    
    # Verify deletion
    conversation = await seeded_session.get(Conversation, "conv-a1-1")
    assert conversation is None


@pytest.mark.asyncio
async def test_delete_returns_false_for_cross_tenant_conversation(
    seeded_session: AsyncSession,
) -> None:
    """Test delete returns False for cross-tenant access."""
    repo = TenantScopedConversationRepository(seeded_session)
    
    # Tenant A tries to delete Tenant B's conversation
    deleted = await repo.delete("conv-b1-1", "tenant-a")
    
    assert deleted is False
    
    # Verify conversation still exists
    conversation = await seeded_session.get(Conversation, "conv-b1-1")
    assert conversation is not None


@pytest.mark.asyncio
async def test_delete_returns_false_for_nonexistent_conversation(
    seeded_session: AsyncSession,
) -> None:
    """Test delete returns False for nonexistent conversation."""
    repo = TenantScopedConversationRepository(seeded_session)
    
    deleted = await repo.delete("nonexistent", "tenant-a")
    
    assert deleted is False


@pytest.mark.asyncio
async def test_delete_verifies_agent_ownership(
    seeded_session: AsyncSession,
) -> None:
    """Test delete verifies agent ownership before deletion."""
    repo = TenantScopedConversationRepository(seeded_session)
    
    # Tenant B can delete their own conversation
    deleted_b = await repo.delete("conv-b1-1", "tenant-b")
    assert deleted_b is True
    
    # Tenant A cannot delete Tenant B's conversation (even after it's deleted)
    deleted_a = await repo.delete("conv-b1-1", "tenant-a")
    assert deleted_a is False


@pytest.mark.asyncio
async def test_list_by_agent_different_agents_same_tenant(
    seeded_session: AsyncSession,
) -> None:
    """Test list_by_agent correctly separates agents within same tenant."""
    repo = TenantScopedConversationRepository(seeded_session)
    
    # Agent A1
    conversations_a1 = await repo.list_by_agent("agent-a1", "tenant-a")
    assert len(conversations_a1) == 2
    assert all(conv.agent_id == "agent-a1" for conv in conversations_a1)
    
    # Agent A2
    conversations_a2 = await repo.list_by_agent("agent-a2", "tenant-a")
    assert len(conversations_a2) == 1
    assert conversations_a2[0].agent_id == "agent-a2"


@pytest.mark.asyncio
async def test_conversation_belongs_to_tenant_through_agent(
    seeded_session: AsyncSession,
) -> None:
    """Test conversation inherits tenant ownership through agent relationship."""
    # Verify database schema: Conversation -> Agent -> Tenant
    result = await seeded_session.execute(
        select(Conversation, Agent, Tenant)
        .join(Agent, Conversation.agent_id == Agent.id)
        .join(Tenant, Agent.tenant_id == Tenant.id)
        .where(Conversation.id == "conv-a1-1")
    )
    row = result.first()
    
    assert row is not None
    conversation, agent, tenant = row
    assert conversation.id == "conv-a1-1"
    assert agent.id == "agent-a1"
    assert tenant.id == "tenant-a"
