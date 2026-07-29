"""Pytest fixtures for API tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.auth.security import hash_api_key
from backend.app.db.base import Base, get_db
from backend.app.db.models import Agent, ApiKey, Client
from backend.app.main import app

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_client_record(db):
    """Create a test client in database."""
    client = Client(
        id="test-client-1",
        name="Test Client",
        is_active=True,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@pytest.fixture
def test_agent(db, test_client_record):
    """Create a test agent in database."""
    agent = Agent(
        id="test-agent-1",
        client_id=test_client_record.id,
        name="Test Agent",
        system_prompt="You are a helpful assistant.",
        is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@pytest.fixture
def test_api_key(db, test_client_record):
    """Create a test API key in database."""
    plain_key = "test-api-key-12345"
    api_key = ApiKey(
        client_id=test_client_record.id,
        key_hash=hash_api_key(plain_key),
        name="Test Key",
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return plain_key, api_key


@pytest.fixture
def another_client_record(db):
    """Create another client for isolation tests."""
    client = Client(
        id="test-client-2",
        name="Another Client",
        is_active=True,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@pytest.fixture
def another_agent(db, another_client_record):
    """Create an agent for another client."""
    agent = Agent(
        id="test-agent-2",
        client_id=another_client_record.id,
        name="Another Agent",
        is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent
