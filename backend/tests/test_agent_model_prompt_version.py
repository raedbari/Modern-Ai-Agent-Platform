"""
Tests for Agent model prompt_version field and migration.

Verifies:
- ORM schema includes a non-null prompt_version column
- Python and database defaults are 'v1'
- ORM and domain models accept custom versions
"""
from sqlalchemy import String

from backend.app.db.models import Agent
from backend.app.domain.models.agent import Agent as DomainAgent


class TestAgentPromptVersionField:
    """Test suite for Agent.prompt_version field."""

    def test_agent_model_has_prompt_version_column(self):
        """Verify prompt_version column exists in database schema."""
        column = Agent.__table__.columns["prompt_version"]

        assert isinstance(column.type, String)
        assert column.type.length == 64
        assert column.nullable is False

    def test_agent_default_prompt_version(self):
        """Verify Python and database defaults both use ``v1``."""
        column = Agent.__table__.columns["prompt_version"]

        assert column.default is not None
        assert column.default.arg == "v1"
        assert column.server_default is not None
        assert str(column.server_default.arg) == "v1"

    def test_agent_custom_prompt_version(self):
        """Verify custom prompt_version values are stored correctly."""
        custom_version = "v2-experimental"
        agent = Agent(
            id="test-agent",
            tenant_id="test-tenant",
            name="Test Agent",
            system_prompt="You are a helpful assistant.",
            prompt_version=custom_version,
        )

        assert agent.prompt_version == custom_version

    def test_domain_agent_includes_prompt_version(self):
        """Verify domain Agent model includes prompt_version field."""
        domain_agent = DomainAgent(
            id="test-id",
            tenant_id="tenant-1",
            prompt_version="v2",
        )

        assert hasattr(domain_agent, "prompt_version")
        assert domain_agent.prompt_version == "v2"

    def test_prompt_version_accepts_various_formats(self):
        """Verify prompt_version accepts various version formats."""
        version_formats = [
            "v1",
            "v2.0",
            "v1.5-beta",
            "2024-01-15",
            "main",
            "experimental-rag-v3"
        ]

        for version in version_formats:
            agent = Agent(
                id=f"agent-{version}",
                tenant_id="test-tenant",
                name=f"Agent {version}",
                system_prompt="Test",
                prompt_version=version,
            )

            assert agent.prompt_version == version, (
                f"Version '{version}' not stored correctly"
            )
