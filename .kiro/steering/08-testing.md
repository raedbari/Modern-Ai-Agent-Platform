# 08-testing: Testing Strategy and Standards

## Purpose

This document defines the testing strategy, standards, and practices for the Modern AI Agent Platform. It establishes test types, coverage requirements, testing tools, test organization, quality gates, and patterns for testing multi-tenant systems and AI components. This document focuses exclusively on testing—ensuring code correctness, reliability, and maintainability through automated verification.

## Testing Philosophy

### Tests are Documentation

Tests document how the system behaves. They demonstrate usage patterns, edge cases, and expected outcomes. Well-written tests serve as living documentation that never goes out of date.

### Tests Enable Refactoring

Tests provide confidence to refactor and improve code. If tests pass after refactoring, behavior is preserved. Without tests, refactoring is dangerous and avoided.

### Tests Catch Regressions

Tests prevent regressions. When a bug is fixed, a test is written to prevent the bug from reoccurring. Over time, the test suite protects against previously discovered issues.

### Write Tests First (When Possible)

Writing tests before implementation (TDD) clarifies requirements and drives better design. Writing tests alongside implementation is acceptable. Writing tests after implementation is necessary but riskier.

### Test Behavior, Not Implementation

Tests verify behavior, not internal implementation details. If implementation changes without changing behavior, tests should still pass. Tests that break when internals change are brittle and costly.

### Tests Must Be Fast

Slow tests discourage running them. Unit tests should run in milliseconds. Integration tests should run in seconds. The full test suite should run in minutes. Optimize tests for speed.

### Tests Must Be Reliable

Flaky tests erode trust in the test suite. Tests must be deterministic and repeatable. Tests that pass sometimes and fail other times are worse than no tests.

### Tests Must Be Independent

Tests do not depend on each other. Each test runs in isolation. Tests can run in any order without affecting outcomes. Shared test state creates fragile, difficult-to-debug tests.

## Test Types

### Unit Tests

**Purpose**: Test individual functions, methods, or classes in isolation.

**Scope**:
- Single function or method
- Isolated from external dependencies (databases, APIs, file systems)
- Mock or stub dependencies
- Fast execution (milliseconds)

**What to Test**:
- Business logic correctness
- Edge cases and boundary conditions
- Error handling and validation
- Domain entity behavior
- Utility functions

**Example**:
```python
def test_agent_name_validation():
    # Given: Invalid agent name
    name = "ab"
    
    # When/Then: Creating agent raises validation error
    with pytest.raises(ValueError, match="Agent name must be at least 3 characters"):
        Agent(tenant_id="tenant_123", name=name, instructions="Test instructions")
```

**Unit Test Coverage Target**: 80% minimum for business logic

### Integration Tests

**Purpose**: Test interactions between components and external systems.

**Scope**:
- Multiple components working together
- Real database interactions (test database)
- Real API client interactions (mock external APIs)
- Slower execution (seconds)

**What to Test**:
- Repository operations (database queries)
- Service interactions
- API endpoint behavior (request/response)
- Authentication and authorization flows
- Tenant isolation enforcement

**Example**:
```python
def test_create_agent_endpoint(test_client, auth_token):
    # Given: Valid agent creation request
    request_data = {
        "name": "Test Agent",
        "instructions": "Test instructions"
    }
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # When: POST /agents
    response = test_client.post("/agents", json=request_data, headers=headers)
    
    # Then: Agent is created and returned
    assert response.status_code == 201
    assert response.json()["name"] == "Test Agent"
```

**Integration Test Coverage Target**: 70% minimum for API endpoints and critical workflows

### End-to-End Tests

**Purpose**: Test complete user workflows from start to finish.

**Scope**:
- Full system integration
- Real user interactions
- Complete workflows (create agent, upload knowledge, generate response)
- Slowest execution (seconds to minutes)

**What to Test**:
- Critical user journeys
- Multi-step workflows
- System behavior under realistic conditions
- Frontend-to-backend integration (when frontend is mature)

**Example**:
```python
def test_agent_creation_and_chat_workflow(test_client, auth_token):
    # Create agent
    agent_response = test_client.post(
        "/agents",
        json={"name": "Support Agent", "instructions": "Help customers"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    agent_id = agent_response.json()["id"]
    
    # Upload knowledge
    knowledge_response = test_client.post(
        f"/agents/{agent_id}/knowledge",
        files={"file": ("faq.txt", b"Q: Hours? A: 9-5 Mon-Fri")},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert knowledge_response.status_code == 201
    
    # Chat with agent
    chat_response = test_client.post(
        f"/agents/{agent_id}/chat",
        json={"message": "What are your hours?"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert "9-5" in chat_response.json()["response"]
```

**End-to-End Test Coverage Target**: Critical user journeys (5-10 key workflows)

### Property-Based Tests

**Purpose**: Test universal properties that must hold for all inputs.

**Scope**:
- Test properties across a wide range of automatically generated inputs
- Verify invariants and universal rules
- Discover edge cases and unexpected failures
- Applicable when properties can be expressed formally

**What to Test**:
- Correctness properties (from design documents)
- Invariants (e.g., "tenant_id is always present in queries")
- Reversibility (e.g., "encode then decode returns original")
- Idempotency (e.g., "running operation twice produces same result")

**Example**:
```python
from hypothesis import given, strategies as st

@given(st.text(min_size=3, max_size=100))
def test_agent_name_accepts_any_valid_string(name):
    # Property: Any string of length 3-100 is a valid agent name
    agent = Agent(tenant_id="tenant_123", name=name, instructions="Test")
    assert agent.name == name.strip()
```

**Property-Based Test Usage**: Apply when correctness properties are defined in design

See #[[file:04-coding-standards.md]] for code quality requirements.

## Testing Tools

### Backend Testing (Python)

**Test Framework**: pytest
- Powerful, flexible, widely used
- Rich plugin ecosystem
- Excellent fixture support

**Assertion Library**: Built-in assert statements
- Clear, readable assertions
- Detailed failure messages

**Mocking**: pytest-mock and unittest.mock
- Mock external dependencies (APIs, databases)
- Stub return values
- Verify function calls

**Test Database**: SQLite in-memory or PostgreSQL test instance
- Real database operations without affecting production
- Fast setup and teardown
- Isolated test data

**Property-Based Testing**: Hypothesis
- Generate test inputs automatically
- Discover edge cases
- Test universal properties

**Example pytest Configuration** (pytest.ini):
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = 
    --verbose
    --cov=app
    --cov-report=html
    --cov-report=term-missing
```

### Frontend Testing (TypeScript/React)

**Test Framework**: Vitest (or Jest)
- Fast, modern testing framework
- Compatible with Vite and TypeScript
- Excellent React support

**Component Testing**: React Testing Library
- Test components from user perspective
- Focus on behavior, not implementation
- Encourages accessible design

**Mocking**: Vitest mocks
- Mock API calls
- Mock external dependencies
- Stub return values

**Example Vitest Configuration** (vitest.config.ts):
```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      lines: 80,
    },
  },
});
```

## Test Organization

### Directory Structure

**Backend** (`backend/tests/`):
```
tests/
├── unit/                    # Unit tests
│   ├── domain/              # Domain entity tests
│   ├── services/            # Service tests
│   └── utils/               # Utility function tests
├── integration/             # Integration tests
│   ├── api/                 # API endpoint tests
│   ├── repositories/        # Repository tests
│   └── workflows/           # Multi-component workflow tests
├── e2e/                     # End-to-end tests
│   └── user_journeys/       # Complete user workflow tests
├── fixtures/                # Shared test fixtures
├── conftest.py              # Pytest configuration
└── __init__.py
```

**Frontend** (`frontend/tests/` or co-located):
```
src/
├── components/
│   ├── AgentList/
│   │   ├── AgentList.tsx
│   │   └── AgentList.test.tsx  # Co-located tests
│   └── KnowledgeUpload/
│       ├── KnowledgeUpload.tsx
│       └── KnowledgeUpload.test.tsx
└── lib/
    ├── api.ts
    └── api.test.ts
```

### Test Naming Conventions

**Test File Naming**:
- Backend: `test_<module_name>.py`
- Frontend: `<component_name>.test.tsx` or `<module_name>.test.ts`

**Test Function Naming**:
- Descriptive names that explain what is being tested
- Pattern: `test_<action>_<expected_outcome>`
- Examples:
  - `test_create_agent_with_valid_data_returns_agent`
  - `test_create_agent_without_tenant_context_raises_error`
  - `test_retrieve_knowledge_scopes_by_tenant_and_agent`

**Test Structure**:
- Follow Arrange-Act-Assert (AAA) pattern
- Or Given-When-Then (GWT) pattern
- Clear separation of setup, execution, and verification

**Example**:
```python
def test_create_agent_validates_name_length():
    # Arrange / Given: Invalid agent name (too short)
    tenant_id = "tenant_123"
    name = "ab"
    instructions = "Test instructions"
    
    # Act / When: Attempt to create agent
    # Assert / Then: Validation error is raised
    with pytest.raises(ValueError, match="Agent name must be at least 3 characters"):
        Agent(tenant_id=tenant_id, name=name, instructions=instructions)
```

## Test Coverage

### Coverage Requirements

- **Unit Tests**: Minimum 80% line coverage for business logic
- **Integration Tests**: Minimum 70% coverage for API endpoints
- **Critical Paths**: 100% coverage for authentication, authorization, tenant isolation, payment processing

**Coverage Measurement**:
- Backend: pytest-cov
- Frontend: Vitest coverage

**Coverage Reports**:
- Generate HTML reports for detailed analysis
- Include coverage reports in CI/CD pipeline
- Fail builds if coverage drops below threshold

**Configuration**:
```bash
# Backend: Run tests with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Frontend: Run tests with coverage
npm test -- --coverage
```

### Coverage Exclusions

**Do not require 100% coverage for**:
- Configuration files
- Test utilities
- Generated code
- Deprecated code (pending removal)

**Focus coverage on**:
- Business logic
- Domain entities
- API endpoints
- Authorization checks
- Tenant isolation enforcement

## Quality Gates

### When Tests Must Pass

**Before Committing**:
- Run relevant unit tests
- Fix failing tests before committing

**Before Creating Pull Request**:
- Run full test suite
- All tests must pass
- Coverage must meet minimums

**Before Merging Pull Request**:
- All tests must pass in CI/CD pipeline
- Code coverage must meet minimums
- No new failing tests introduced

**CI/CD Pipeline**:
- Run tests automatically on every push
- Block merges if tests fail
- Report coverage metrics

### Running Tests Locally

**Backend**:
```bash
# Run all tests
cd backend
pytest

# Run specific test file
pytest tests/unit/test_agent.py

# Run tests matching pattern
pytest -k "test_agent"

# Run with coverage
pytest --cov=app --cov-report=html
```

**Frontend**:
```bash
# Run all tests
cd frontend
npm test

# Run specific test file
npm test -- AgentList.test.tsx

# Run with coverage
npm test -- --coverage
```

## Multi-Tenant Testing Patterns

Multi-tenancy requires special testing focus to ensure tenant isolation is never violated.

### Test Tenant Isolation in Queries

**Every query that accesses tenant data must be tested for tenant isolation**:

```python
def test_find_agents_scopes_by_tenant(agent_repository):
    # Arrange: Create agents for two different tenants
    tenant_a = "tenant_a"
    tenant_b = "tenant_b"
    
    agent_a1 = Agent(tenant_id=tenant_a, name="Agent A1", instructions="Test")
    agent_a2 = Agent(tenant_id=tenant_a, name="Agent A2", instructions="Test")
    agent_b1 = Agent(tenant_id=tenant_b, name="Agent B1", instructions="Test")
    
    agent_repository.save(agent_a1)
    agent_repository.save(agent_a2)
    agent_repository.save(agent_b1)
    
    # Act: Retrieve agents for tenant A
    agents = agent_repository.find_by_tenant(tenant_a)
    
    # Assert: Only tenant A's agents are returned
    assert len(agents) == 2
    assert all(agent.tenant_id == tenant_a for agent in agents)
```

### Test Tenant Ownership Verification

**Test that operations reject access to other tenants' data**:

```python
def test_get_agent_rejects_cross_tenant_access(agent_service):
    # Arrange: Create agent for tenant A
    tenant_a = "tenant_a"
    tenant_b = "tenant_b"
    agent = agent_service.create_agent(tenant_a, "Agent A", "Test instructions")
    
    # Act/Assert: Tenant B cannot access tenant A's agent
    with pytest.raises(UnauthorizedAccessException):
        agent_service.get_agent_by_id(agent.id, tenant_b)
```

### Test Knowledge Retrieval Scoping

**Test that knowledge retrieval is scoped by tenant and agent**:

```python
def test_retrieve_knowledge_scopes_by_tenant_and_agent(knowledge_service):
    # Arrange: Create two agents with different knowledge
    agent_a = create_agent(tenant_id="tenant_a", name="Agent A")
    agent_b = create_agent(tenant_id="tenant_b", name="Agent B")
    
    upload_knowledge(agent_a.id, "Agent A knowledge")
    upload_knowledge(agent_b.id, "Agent B knowledge")
    
    # Act: Retrieve knowledge for agent A
    chunks = knowledge_service.retrieve_relevant_chunks(
        tenant_id="tenant_a",
        agent_id=agent_a.id,
        query="test query"
    )
    
    # Assert: Only agent A's knowledge is retrieved
    assert all("Agent A knowledge" in chunk.content for chunk in chunks)
```

### Test API Authorization

**Test that API endpoints enforce tenant authorization**:

```python
def test_get_agent_endpoint_requires_tenant_ownership(test_client):
    # Arrange: Create agent for tenant A
    tenant_a_token = create_auth_token(tenant_id="tenant_a")
    tenant_b_token = create_auth_token(tenant_id="tenant_b")
    
    response = test_client.post(
        "/agents",
        json={"name": "Agent A", "instructions": "Test"},
        headers={"Authorization": f"Bearer {tenant_a_token}"}
    )
    agent_id = response.json()["id"]
    
    # Act: Tenant B attempts to access tenant A's agent
    response = test_client.get(
        f"/agents/{agent_id}",
        headers={"Authorization": f"Bearer {tenant_b_token}"}
    )
    
    # Assert: Access is denied
    assert response.status_code == 403
```

## AI-Specific Testing Patterns

Testing AI components requires special patterns to handle non-deterministic behavior and external dependencies.

### Mock LLM Responses

**Mock language model API calls for predictable testing**:

```python
from unittest.mock import Mock, patch

def test_generate_response_with_knowledge(rag_pipeline, mocker):
    # Arrange: Mock AI provider
    mock_ai_client = mocker.patch("app.services.ai_client.generate_completion")
    mock_ai_client.return_value = "Based on the documentation, the answer is X."
    
    # Act: Generate response
    response = rag_pipeline.generate_response(
        tenant_id="tenant_123",
        agent_id="agent_456",
        message="What is X?"
    )
    
    # Assert: Response is generated
    assert "answer is X" in response
    mock_ai_client.assert_called_once()
```

### Test Knowledge Retrieval

**Test semantic search with known queries and expected results**:

```python
def test_retrieve_knowledge_returns_relevant_chunks(knowledge_service):
    # Arrange: Upload knowledge with known content
    agent_id = create_test_agent()
    upload_knowledge(agent_id, "The platform supports multi-tenancy.")
    upload_knowledge(agent_id, "Agents can be customized with instructions.")
    
    # Act: Retrieve knowledge with specific query
    chunks = knowledge_service.retrieve_relevant_chunks(
        tenant_id="tenant_123",
        agent_id=agent_id,
        query="Does the platform support multiple tenants?"
    )
    
    # Assert: Relevant chunk is returned
    assert len(chunks) > 0
    assert "multi-tenancy" in chunks[0].content
```

### Test Prompt Construction

**Test that prompts include all required components**:

```python
def test_construct_prompt_includes_all_components(rag_pipeline):
    # Arrange: Set up agent with instructions and knowledge
    agent = create_agent_with_knowledge()
    conversation_history = [
        Message(role="user", content="Hello"),
        Message(role="agent", content="Hi, how can I help?")
    ]
    
    # Act: Construct prompt
    prompt = rag_pipeline.construct_prompt(
        agent=agent,
        context="Retrieved knowledge context",
        conversation_history=conversation_history,
        user_message="What can you do?"
    )
    
    # Assert: Prompt includes all components
    assert "System Prompt" in prompt or agent.system_prompt in prompt
    assert agent.instructions in prompt
    assert "Retrieved knowledge context" in prompt
    assert "Hello" in prompt  # Conversation history
    assert "What can you do?" in prompt  # User message
```

### Test Out-of-Scope Behavior

**Test that agents return out-of-scope responses when knowledge is insufficient**:

```python
def test_agent_returns_out_of_scope_response_when_knowledge_insufficient(rag_pipeline, mocker):
    # Arrange: Empty knowledge base
    agent = create_agent_without_knowledge()
    
    # Mock retrieval to return no results
    mocker.patch.object(
        rag_pipeline._knowledge_service,
        "retrieve_relevant_chunks",
        return_value=[]
    )
    
    # Act: Ask question with no relevant knowledge
    response = rag_pipeline.generate_response(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        message="What is the capital of France?"
    )
    
    # Assert: Out-of-scope response is returned
    assert "don't have information" in response.lower() or "outside my knowledge" in response.lower()
```

### Test Embedding Generation

**Test that embeddings are generated and stored correctly**:

```python
def test_generate_embedding_stores_vector(embedding_service, mocker):
    # Arrange: Mock embedding API
    mock_embedding = [0.1, 0.2, 0.3, ...]  # 1536 dimensions
    mocker.patch.object(
        embedding_service._ai_client,
        "create_embedding",
        return_value=mock_embedding
    )
    
    # Act: Generate embedding
    text = "Test knowledge chunk"
    embedding = embedding_service.generate_embedding(text)
    
    # Assert: Embedding is returned
    assert len(embedding) == 1536
    assert embedding == mock_embedding
```

## Test Fixtures

### Shared Test Fixtures (Backend)

**conftest.py**:
```python
import pytest
from app.main import app
from app.database import get_db, Base, engine
from fastapi.testclient import TestClient

@pytest.fixture
def test_db():
    """Create test database and tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_client(test_db):
    """Create FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def auth_token():
    """Generate authentication token for testing."""
    return generate_test_token(tenant_id="tenant_123", user_id="user_456")

@pytest.fixture
def test_agent():
    """Create test agent."""
    return Agent(
        tenant_id="tenant_123",
        name="Test Agent",
        instructions="Test instructions"
    )
```

### Test Data Builders

**Use builder pattern for complex test data**:

```python
class AgentBuilder:
    def __init__(self):
        self.tenant_id = "tenant_123"
        self.name = "Test Agent"
        self.instructions = "Test instructions"
        self.model = "gpt-4"
    
    def with_tenant(self, tenant_id: str):
        self.tenant_id = tenant_id
        return self
    
    def with_name(self, name: str):
        self.name = name
        return self
    
    def build(self) -> Agent:
        return Agent(
            tenant_id=self.tenant_id,
            name=self.name,
            instructions=self.instructions,
            model=self.model
        )

# Usage
agent = AgentBuilder().with_tenant("tenant_456").with_name("Custom Agent").build()
```

## Common Testing Anti-Patterns

### Avoid These Patterns

**Fragile Tests**:
- Tests that break when implementation details change
- Tests tightly coupled to internal structure
- Solution: Test behavior, not implementation

**Slow Tests**:
- Tests that perform expensive operations unnecessarily
- Tests that don't use appropriate mocking
- Solution: Mock external dependencies, use in-memory databases

**Flaky Tests**:
- Tests that pass sometimes and fail other times
- Tests that depend on timing or external state
- Solution: Make tests deterministic, avoid race conditions

**Interdependent Tests**:
- Tests that depend on execution order
- Tests that share mutable state
- Solution: Ensure tests are independent and isolated

**Unclear Tests**:
- Tests with vague names
- Tests without clear arrange-act-assert structure
- Solution: Use descriptive names, follow AAA pattern

## References

- Code quality requirements: #[[file:04-coding-standards.md]]
- AI component patterns: #[[file:06-ai-platform.md]]
- Security testing: #[[file:07-security.md]]
- Completion criteria: #[[file:09-definition-of-done.md]]

## Document Boundaries

This document defines testing strategy and standards only. It establishes test types, coverage requirements, testing tools, and quality gates.

**This document must never contain:**

- **Implementation code**: Actual production code, detailed algorithms, or business logic belong in source files.
- **Coding standards**: General code quality, naming conventions, or organization rules belong in #[[file:04-coding-standards.md]].
- **Architecture**: System layers, component boundaries, or dependency rules belong in #[[file:03-system-architecture.md]].
- **Security policies**: Authentication, authorization, or secret management belong in #[[file:07-security.md]].
- **Domain definitions**: Entity definitions, relationships, or business rules belong in #[[file:02-domain-model.md]].

This document focuses exclusively on **testing** (test types, coverage requirements, testing tools, test organization, quality gates, and testing patterns for multi-tenant and AI systems).

When questions arise about other topics, refer to the appropriate steering document.
