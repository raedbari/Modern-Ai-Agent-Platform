"""Tests for trusted multi-tenant customer bootstrap operations."""

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.auth.api_keys import parse_api_key, verify_api_key_secret
from backend.app.db.base import Base
from backend.app.db.models import Agent, ApiKey, Tenant
from backend.app.operations.customer_bootstrap import (
    BootstrapConflictError,
    bootstrap_customer,
)


async def _session_factory(database_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


@pytest.mark.asyncio
async def test_bootstrap_creates_scoped_customer_and_hashed_key(
    tmp_path: Path,
) -> None:
    engine, sessions = await _session_factory(tmp_path / "bootstrap.sqlite3")
    try:
        async with sessions() as session:
            result = await bootstrap_customer(
                session,
                tenant_id="tenant-a",
                tenant_name="Tenant A",
                agent_id="agent-a",
                agent_name="Agent A",
                system_prompt="Use verified knowledge.",
                contact_message=(
                    "Contact support at support@example.test or 012345678."
                ),
                key_name="local-server",
            )
            await session.commit()

        parsed = parse_api_key(result.api_key)
        assert parsed is not None
        key_id, secret = parsed

        async with sessions() as session:
            tenant = await session.get(Tenant, "tenant-a")
            agent = await session.get(Agent, "agent-a")
            key = await session.scalar(
                select(ApiKey).where(ApiKey.key_id == key_id)
            )

        assert tenant is not None
        assert agent is not None
        assert agent.tenant_id == tenant.id
        assert agent.system_prompt == "Use verified knowledge."
        assert agent.contact_message == (
            "Contact support at support@example.test or 012345678."
        )
        assert key is not None
        assert key.tenant_id == tenant.id
        assert result.api_key not in key.key_digest
        assert verify_api_key_secret(secret, key.key_digest)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_bootstrap_refuses_duplicate_active_named_key(
    tmp_path: Path,
) -> None:
    engine, sessions = await _session_factory(tmp_path / "duplicate.sqlite3")
    try:
        async with sessions() as session:
            await bootstrap_customer(
                session,
                tenant_id="tenant-a",
                tenant_name="Tenant A",
                agent_id="agent-a",
                agent_name="Agent A",
                system_prompt=None,
                key_name="local-server",
            )
            await session.commit()

        async with sessions() as session:
            with pytest.raises(
                BootstrapConflictError,
                match="already exists",
            ):
                await bootstrap_customer(
                    session,
                    tenant_id="tenant-a",
                    tenant_name="Tenant A",
                    agent_id="agent-a",
                    agent_name="Agent A",
                    system_prompt=None,
                    key_name="local-server",
                )
            await session.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_bootstrap_rotates_only_the_matching_named_key(
    tmp_path: Path,
) -> None:
    engine, sessions = await _session_factory(tmp_path / "rotate.sqlite3")
    try:
        async with sessions() as session:
            first = await bootstrap_customer(
                session,
                tenant_id="tenant-a",
                tenant_name="Tenant A",
                agent_id="agent-a",
                agent_name="Agent A",
                system_prompt=None,
                key_name="local-server",
            )
            await session.commit()

        async with sessions() as session:
            second = await bootstrap_customer(
                session,
                tenant_id="tenant-a",
                tenant_name="Tenant A",
                agent_id="agent-a",
                agent_name="Agent A",
                system_prompt=None,
                key_name="local-server",
                rotate_key=True,
            )
            await session.commit()

        assert first.api_key != second.api_key
        assert second.rotated_key_count == 1

        async with sessions() as session:
            keys = list(
                (
                    await session.scalars(
                        select(ApiKey).where(
                            ApiKey.tenant_id == "tenant-a"
                        )
                    )
                ).all()
            )
        assert len(keys) == 2
        assert sum(key.is_active for key in keys) == 1
        assert sum(key.revoked_at is not None for key in keys) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_bootstrap_refuses_cross_tenant_agent_id_reuse(
    tmp_path: Path,
) -> None:
    engine, sessions = await _session_factory(tmp_path / "scope.sqlite3")
    try:
        async with sessions() as session:
            session.add_all(
                [
                    Tenant(id="tenant-a", name="Tenant A"),
                    Tenant(id="tenant-b", name="Tenant B"),
                    Agent(
                        id="shared-agent",
                        tenant_id="tenant-a",
                        name="Agent A",
                    ),
                ]
            )
            await session.commit()

        async with sessions() as session:
            with pytest.raises(
                BootstrapConflictError,
                match="another tenant",
            ):
                await bootstrap_customer(
                    session,
                    tenant_id="tenant-b",
                    tenant_name="Tenant B",
                    agent_id="shared-agent",
                    agent_name="Agent B",
                    system_prompt=None,
                    key_name="local-server",
                )
            await session.rollback()
    finally:
        await engine.dispose()
