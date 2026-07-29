"""Shared test fixtures for all tests."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.config import Settings
from backend.app.db.base import Base
from backend.app.db.models import Agent, ApiKey, Tenant
from backend.app.db.utils import create_api_key_for_tenant


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Override settings for testing."""
    return Settings(
        environment="test",
        database_url="postgresql+asyncpg://maap:maap@localhost:5432/maap_test",
        database_echo=False,
        deepseek_api_key=None,
    )


@pytest_asyncio.fixture(scope="function")
async def db_engine(test_settings: Settings):
    """Create a test database engine."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=test_settings.database_echo,
        pool_pre_ping=True,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def tenant1(db_session: AsyncSession) -> Tenant:
    """Create a test tenant 1."""
    tenant = Tenant(
        id="tenant-1",
        name="Test Tenant 1",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def tenant2(db_session: AsyncSession) -> Tenant:
    """Create a test tenant 2."""
    tenant = Tenant(
        id="tenant-2",
        name="Test Tenant 2",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def inactive_tenant(db_session: AsyncSession) -> Tenant:
    """Create an inactive test tenant."""
    tenant = Tenant(
        id="tenant-inactive",
        name="Inactive Tenant",
        is_active=False,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def api_key_tenant1(
    db_session: AsyncSession, tenant1: Tenant
) -> tuple[ApiKey, str]:
    """Create an API key for tenant 1."""
    return await create_api_key_for_tenant(
        db_session, tenant1.id, "Tenant 1 Key"
    )


@pytest_asyncio.fixture
async def api_key_tenant2(
    db_session: AsyncSession, tenant2: Tenant
) -> tuple[ApiKey, str]:
    """Create an API key for tenant 2."""
    return await create_api_key_for_tenant(
        db_session, tenant2.id, "Tenant 2 Key"
    )


@pytest_asyncio.fixture
async def revoked_api_key(
    db_session: AsyncSession, tenant1: Tenant
) -> tuple[ApiKey, str]:
    """Create a revoked API key."""
    api_key, plain_key = await create_api_key_for_tenant(
        db_session, tenant1.id, "Revoked Key"
    )
    api_key.is_active = False
    await db_session.commit()
    await db_session.refresh(api_key)
    return api_key, plain_key


@pytest_asyncio.fixture
async def agent_tenant1(db_session: AsyncSession, tenant1: Tenant) -> Agent:
    """Create an agent for tenant 1."""
    agent = Agent(
        id="agent-t1",
        tenant_id=tenant1.id,
        name="Tenant 1 Agent",
        description="Test agent for tenant 1",
        system_prompt="You are a helpful assistant.",
        is_active=True,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest_asyncio.fixture
async def agent_tenant2(db_session: AsyncSession, tenant2: Tenant) -> Agent:
    """Create an agent for tenant 2."""
    agent = Agent(
        id="agent-t2",
        tenant_id=tenant2.id,
        name="Tenant 2 Agent",
        description="Test agent for tenant 2",
        system_prompt="You are a helpful assistant.",
        is_active=True,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent
