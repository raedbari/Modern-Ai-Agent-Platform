"""Script to create test data for development and manual testing."""

from backend.app.auth.security import hash_api_key
from backend.app.db.base import SessionLocal, engine
from backend.app.db.models import Agent, ApiKey, Base, Client

# Create tables
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

try:
    # Create test client
    client = Client(
        id="demo-client-1",
        name="Demo Client",
        is_active=True,
    )
    db.add(client)
    
    # Create test agent
    agent = Agent(
        id="demo-agent-1",
        client_id=client.id,
        name="Demo Support Agent",
        system_prompt="You are a helpful customer support assistant. Be friendly and professional.",
        is_active=True,
    )
    db.add(agent)
    
    # Create API key
    plain_key = "demo-api-key-12345678"
    api_key = ApiKey(
        client_id=client.id,
        key_hash=hash_api_key(plain_key),
        name="Demo API Key",
        is_active=True,
    )
    db.add(api_key)
    
    db.commit()
    
    print("✓ Test data created successfully!")
    print("\n" + "="*60)
    print("Test Credentials:")
    print("="*60)
    print(f"Client ID: {client.id}")
    print(f"Agent ID: {agent.id}")
    print(f"API Key: {plain_key}")
    print("="*60)
    print("\nExample curl command:")
    print(f"""
curl -X POST http://localhost:8000/v1/chat \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: {plain_key}" \\
  -d '{{
    "agent_id": "{agent.id}",
    "message": "Hello! Can you help me?"
  }}'
""")
    
except Exception as e:
    print(f"Error creating test data: {e}")
    db.rollback()
finally:
    db.close()
