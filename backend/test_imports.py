"""Test script to verify all imports work."""

try:
    print("Testing imports...")
    
    print("1. Testing db.base...")
    from backend.app.db.base import Base, TimestampMixin
    print("   ✓ db.base OK")
    
    print("2. Testing db.models...")
    from backend.app.db.models import Tenant, ApiKey, Agent, Conversation, Message
    print("   ✓ db.models OK")
    
    print("3. Testing auth.security...")
    from backend.app.auth.security import hash_api_key, verify_api_key
    print("   ✓ auth.security OK")
    
    print("4. Testing auth.models...")
    from backend.app.auth.models import AuthenticatedContext
    print("   ✓ auth.models OK")
    
    print("5. Testing db.utils...")
    from backend.app.db.utils import generate_api_key
    print("   ✓ db.utils OK")
    
    print("\n✅ All imports successful!")
    
except Exception as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
