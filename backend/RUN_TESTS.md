# Test Execution Guide

## Prerequisites

Before running tests, ensure you have:

1. **PostgreSQL running** with test database:
   ```bash
   # Create test database
   createdb maap_test
   # Or with credentials:
   psql -U postgres -c "CREATE DATABASE maap_test;"
   ```

2. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment configured** (optional, defaults are suitable for testing):
   ```bash
   export MAAP_DATABASE_URL="postgresql+asyncpg://maap:maap@localhost:5432/maap_test"
   export MAAP_ENVIRONMENT="test"
   ```

## Running Tests

### Run all tests:
```bash
cd backend
python -m pytest tests/ -v
```

### Run specific test files:
```bash
# Authentication tests
python -m pytest tests/test_auth.py -v

# Tenant isolation tests
python -m pytest tests/test_tenant_isolation.py -v

# Existing tests (should still pass)
python -m pytest tests/test_config.py tests/test_health.py -v
```

### Run with coverage:
```bash
python -m pytest tests/ --cov=backend.app --cov-report=html
```

## Test Structure

### New Tests Added (Phase 1):

1. **tests/test_auth.py** - Authentication tests (15+ tests):
   - API key generation and format validation
   - Key hashing and verification
   - Authentication with valid/invalid/expired/revoked keys  
   - Inactive tenant rejection
   - last_used_at timestamp tracking
   - Cross-tenant key isolation

2. **tests/test_tenant_isolation.py** - Multi-tenant isolation (10+ tests):
   - Agent-tenant relationship verification
   - Conversation-tenant relationship verification
   - Cross-tenant access prevention
   - Agent-conversation-tenant matching
   - Archived conversation filtering

3. **tests/conftest.py** - Shared fixtures:
   - Test database setup/teardown
   - Tenant fixtures (tenant1, tenant2, inactive_tenant)
   - API key fixtures
   - Agent fixtures

### Expected Test Results:

All tests should PASS if:
- PostgreSQL is running
- Test database exists
- All dependencies are installed
- No port conflicts

## Troubleshooting

### Database connection errors:
```bash
# Check PostgreSQL is running
pg_isready

# Verify test database exists
psql -l | grep maap_test

# Check connection string
echo $MAAP_DATABASE_URL
```

### Import errors:
```bash
# Verify you're in backend directory
pwd  # Should end with /backend

# Test imports manually
python test_imports.py
```

### Async test errors:
```bash
# Ensure pytest-asyncio is installed
pip list | grep pytest-asyncio
```

## Test Coverage

Phase 1 implementation includes tests for:

✅ API Key generation (secure, unique, correct format)
✅ Bcrypt hashing (one-way, verification)  
✅ Authentication flow (header extraction, hash verification)
✅ Active/inactive tenant filtering
✅ Key expiration checking
✅ Key revocation handling
✅ Tenant isolation for agents
✅ Tenant isolation for conversations
✅ Cross-tenant access prevention
✅ Agent-conversation-tenant relationship validation
✅ last_used_at tracking

## What's NOT tested yet (Phase 2):

⏭️ Rate limiting
⏭️ Idempotency
⏭️ CORS
⏭️ Chat API endpoints
⏭️ LangGraph integration
⏭️ Message storage
⏭️ Streaming responses
