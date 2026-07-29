"""Tests for tenant isolation in database operations."""

import pytest

from backend.app.db.models import Conversation
from backend.app.db.utils import (
    verify_agent_and_conversation_match,
    verify_agent_belongs_to_tenant,
    verify_conversation_belongs_to_tenant,
    generate_conversation_id,
)


class TestAgentIsolation:
    """Test agent-tenant isolation."""

    @pytest.mark.asyncio
    async def test_verify_agent_belongs_to_correct_tenant(
        self, db_session, tenant1, agent_tenant1
    ):
        """Test that agent verification succeeds for correct tenant."""
        agent = await verify_agent_belongs_to_tenant(
            db_session, agent_tenant1.id, tenant1.id
        )
        
        assert agent is not None
        assert agent.id == agent_tenant1.id
        assert agent.tenant_id == tenant1.id

    @pytest.mark.asyncio
    async def test_verify_agent_rejects_wrong_tenant(
        self, db_session, tenant1, tenant2, agent_tenant1
    ):
        """Test that agent verification fails for wrong tenant."""
        agent = await verify_agent_belongs_to_tenant(
            db_session, agent_tenant1.id, tenant2.id
        )
        
        assert agent is None

    @pytest.mark.asyncio
    async def test_verify_agent_rejects_nonexistent_agent(
        self, db_session, tenant1
    ):
        """Test that verification fails for non-existent agent."""
        agent = await verify_agent_belongs_to_tenant(
            db_session, "nonexistent-agent", tenant1.id
        )
        
        assert agent is None

    @pytest.mark.asyncio
    async def test_tenant2_cannot_access_tenant1_agent(
        self, db_session, tenant1, tenant2, agent_tenant1, agent_tenant2
    ):
        """Test complete isolation between tenant agents."""
        # Tenant 1 can access its own agent
        agent1 = await verify_agent_belongs_to_tenant(
            db_session, agent_tenant1.id, tenant1.id
        )
        assert agent1 is not None
        
        # Tenant 2 cannot access tenant 1's agent
        agent1_wrong = await verify_agent_belongs_to_tenant(
            db_session, agent_tenant1.id, tenant2.id
        )
        assert agent1_wrong is None
        
        # Tenant 2 can access its own agent
        agent2 = await verify_agent_belongs_to_tenant(
            db_session, agent_tenant2.id, tenant2.id
        )
        assert agent2 is not None
        
        # Tenant 1 cannot access tenant 2's agent
        agent2_wrong = await verify_agent_belongs_to_tenant(
            db_session, agent_tenant2.id, tenant1.id
        )
        assert agent2_wrong is None


class TestConversationIsolation:
    """Test conversation-tenant isolation."""

    @pytest.mark.asyncio
    async def test_verify_conversation_belongs_to_correct_tenant(
        self, db_session, tenant1, agent_tenant1
    ):
        """Test that conversation verification succeeds for correct tenant."""
        # Create a conversation
        conv_id = generate_conversation_id()
        conv = Conversation(
            id=conv_id,
            tenant_id=tenant1.id,
            agent_id=agent_tenant1.id,
            title="Test Conversation",
            is_archived=False,
        )
        db_session.add(conv)
        await db_session.commit()
        
        # Verify it belongs to tenant 1
        verified = await verify_conversation_belongs_to_tenant(
            db_session, conv_id, tenant1.id
        )
        
        assert verified is not None
        assert verified.id == conv_id
        assert verified.tenant_id == tenant1.id

    @pytest.mark.asyncio
    async def test_verify_conversation_rejects_wrong_tenant(
        self, db_session, tenant1, tenant2, agent_tenant1
    ):
        """Test that conversation verification fails for wrong tenant."""
        # Create a conversation for tenant 1
        conv_id = generate_conversation_id()
        conv = Conversation(
            id=conv_id,
            tenant_id=tenant1.id,
            agent_id=agent_tenant1.id,
            title="Test Conversation",
            is_archived=False,
        )
        db_session.add(conv)
        await db_session.commit()
        
        # Try to verify with tenant 2
        verified = await verify_conversation_belongs_to_tenant(
            db_session, conv_id, tenant2.id
        )
        
        assert verified is None

    @pytest.mark.asyncio
    async def test_archived_conversations_are_not_accessible(
        self, db_session, tenant1, agent_tenant1
    ):
        """Test that archived conversations are not returned."""
        # Create an archived conversation
        conv_id = generate_conversation_id()
        conv = Conversation(
            id=conv_id,
            tenant_id=tenant1.id,
            agent_id=agent_tenant1.id,
            title="Archived Conversation",
            is_archived=True,
        )
        db_session.add(conv)
        await db_session.commit()
        
        # Try to verify - should fail because it's archived
        verified = await verify_conversation_belongs_to_tenant(
            db_session, conv_id, tenant1.id
        )
        
        assert verified is None


class TestAgentConversationMatch:
    """Test agent-conversation-tenant relationship validation."""

    @pytest.mark.asyncio
    async def test_valid_agent_conversation_match(
        self, db_session, tenant1, agent_tenant1
    ):
        """Test valid agent-conversation-tenant relationship."""
        # Create conversation for agent
        conv_id = generate_conversation_id()
        conv = Conversation(
            id=conv_id,
            tenant_id=tenant1.id,
            agent_id=agent_tenant1.id,
            title="Test",
            is_archived=False,
        )
        db_session.add(conv)
        await db_session.commit()
        
        # Verify the match
        is_valid = await verify_agent_and_conversation_match(
            db_session, agent_tenant1.id, conv_id, tenant1.id
        )
        
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_wrong_agent_for_conversation(
        self, db_session, tenant1, agent_tenant1, agent_tenant2
    ):
        """Test rejection when conversation belongs to different agent."""
        # Create conversation for agent_tenant1
        conv_id = generate_conversation_id()
        conv = Conversation(
            id=conv_id,
            tenant_id=tenant1.id,
            agent_id=agent_tenant1.id,
            title="Test",
            is_archived=False,
        )
        db_session.add(conv)
        await db_session.commit()
        
        # Try to verify with wrong agent (from different tenant)
        is_valid = await verify_agent_and_conversation_match(
            db_session, agent_tenant2.id, conv_id, tenant1.id
        )
        
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_wrong_tenant_for_conversation(
        self, db_session, tenant1, tenant2, agent_tenant1
    ):
        """Test rejection when tenant doesn't match."""
        # Create conversation for tenant1
        conv_id = generate_conversation_id()
        conv = Conversation(
            id=conv_id,
            tenant_id=tenant1.id,
            agent_id=agent_tenant1.id,
            title="Test",
            is_archived=False,
        )
        db_session.add(conv)
        await db_session.commit()
        
        # Try to verify with wrong tenant
        is_valid = await verify_agent_and_conversation_match(
            db_session, agent_tenant1.id, conv_id, tenant2.id
        )
        
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_cross_tenant_access_prevention(
        self, db_session, tenant1, tenant2, agent_tenant1, agent_tenant2
    ):
        """Test complete cross-tenant access prevention."""
        # Create conversation for tenant1
        conv1_id = generate_conversation_id()
        conv1 = Conversation(
            id=conv1_id,
            tenant_id=tenant1.id,
            agent_id=agent_tenant1.id,
            title="Tenant 1 Conv",
            is_archived=False,
        )
        
        # Create conversation for tenant2
        conv2_id = generate_conversation_id()
        conv2 = Conversation(
            id=conv2_id,
            tenant_id=tenant2.id,
            agent_id=agent_tenant2.id,
            title="Tenant 2 Conv",
            is_archived=False,
        )
        
        db_session.add_all([conv1, conv2])
        await db_session.commit()
        
        # Tenant 1 can access its own conversation
        valid1 = await verify_agent_and_conversation_match(
            db_session, agent_tenant1.id, conv1_id, tenant1.id
        )
        assert valid1 is True
        
        # Tenant 2 can access its own conversation
        valid2 = await verify_agent_and_conversation_match(
            db_session, agent_tenant2.id, conv2_id, tenant2.id
        )
        assert valid2 is True
        
        # Tenant 1 cannot access tenant 2's conversation
        invalid1 = await verify_agent_and_conversation_match(
            db_session, agent_tenant1.id, conv2_id, tenant1.id
        )
        assert invalid1 is False
        
        # Tenant 2 cannot access tenant 1's conversation
        invalid2 = await verify_agent_and_conversation_match(
            db_session, agent_tenant2.id, conv1_id, tenant2.id
        )
        assert invalid2 is False
