# 04-coding-standards: Engineering Coding Standards

## Purpose

This document defines HOW code should be written for the Modern AI Agent Platform. It establishes engineering principles, naming conventions, code organization rules, error handling patterns, configuration management, and multi-tenant coding practices. This document focuses exclusively on code quality, structure, and implementation standards—not architecture, business concepts, or workflow.

## General Engineering Principles

### Write Code for Humans

Code is read far more often than written. Optimize for clarity and readability over cleverness. Choose descriptive names, simple logic, and clear structure. If code requires extensive comments to explain what it does, rewrite the code to be self-explanatory.

### Explicit is Better Than Implicit

Make intentions clear. Avoid magic values, hidden behavior, and implicit assumptions. Dependencies, configurations, and tenant context must be explicit. No globals, no hidden state, no surprises.

### Fail Fast and Loudly

Detect errors as early as possible. Validate inputs at system boundaries. Raise explicit exceptions when invariants are violated. Never silently ignore errors or return ambiguous results.

### Immutability by Default

Prefer immutable data structures and operations. Mutability increases complexity and makes reasoning about code difficult. When mutation is necessary, limit its scope and make it explicit.

### Single Responsibility

Each function, class, and module should have one clear responsibility. If a component does multiple things, split it. Single responsibility improves testability, maintainability, and understanding.

### Composition Over Inheritance

Prefer composition and delegation over deep inheritance hierarchies. Inheritance couples classes tightly and makes changes difficult. Composition provides flexibility and clarity.

### Test Your Code

Code without tests is unverified code. Write unit tests for business logic, integration tests for component interactions, and end-to-end tests for critical workflows. Tests serve as living documentation and prevent regressions.

### Keep It Simple

Choose the simplest solution that solves the problem correctly. Avoid premature optimization, over-engineering, and speculative features. Add complexity only when justified by verified requirements.

### No Premature Optimization

Optimize for clarity and correctness first. Optimize for performance only when measurements indicate a problem. Measure before optimizing. Document performance assumptions and constraints.

### Boy Scout Rule

Leave code cleaner than you found it. Fix small issues when you see them. Refactor unclear code. Update outdated comments. Remove dead code. Incremental improvements compound over time.

---

## Project Structure Rules


### Backend Structure

The backend follows a layered directory structure that reflects architectural boundaries:

```
backend/
├── app/
│   ├── api/              # Presentation Layer: API endpoints and routes
│   │   ├── routes/       # Route definitions grouped by resource
│   │   ├── middleware/   # Request/response middleware
│   │   └── schemas/      # Request/response validation schemas
│   ├── application/      # Application Layer: Use cases and orchestration
│   │   ├── use_cases/    # Use case implementations
│   │   └── services/     # Application services
│   ├── domain/           # Domain Layer: Business logic and entities
│   │   ├── entities/     # Domain entities
│   │   ├── repositories/ # Repository interfaces (not implementations)
│   │   └── services/     # Domain services
│   ├── infrastructure/   # Infrastructure Layer: Technical implementations
│   │   ├── database/     # Database access and repositories
│   │   ├── ai/           # AI provider integration
│   │   ├── storage/      # File storage integration
│   │   └── config/       # Configuration management
│   ├── core/             # Shared utilities and cross-cutting concerns
│   │   ├── auth/         # Authentication and authorization
│   │   ├── errors/       # Error definitions and handlers
│   │   └── logging/      # Logging configuration
│   └── main.py           # Application entry point
├── tests/                # Test suite mirroring app structure
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── requirements.txt      # Python dependencies
└── README.md
```


### Frontend Structure

The frontend follows a component-based structure:

```
frontend/
├── src/
│   ├── app/              # Next.js app directory
│   │   ├── (routes)/     # Route groups
│   │   ├── layout.tsx    # Root layout
│   │   └── page.tsx      # Home page
│   ├── components/       # Reusable React components
│   │   ├── ui/           # Basic UI components
│   │   └── features/     # Feature-specific components
│   ├── lib/              # Utilities and helpers
│   ├── hooks/            # Custom React hooks
│   ├── types/            # TypeScript type definitions
│   └── styles/           # Global styles
├── public/               # Static assets
├── package.json
└── README.md
```

### Module Organization

- **Group by feature, not by type**: Organize code by business capability (tenant, agent, knowledge) rather than technical role (controllers, models, views).
- **Collocate related code**: Keep related files together. Tests should live near the code they test.
- **Respect layer boundaries**: Files in the Domain Layer must not import from Application, Infrastructure, or Presentation layers.
- **Explicit dependencies**: Import paths should reflect architectural dependencies. No circular imports.

---

## Naming Conventions


### General Rules

- **Use descriptive names**: Names should reveal intent. Avoid abbreviations unless universally understood (ID, API, URL).
- **Be consistent**: Follow the same naming pattern throughout the codebase.
- **Use domain language**: Use terms from the ubiquitous language defined in #[[file:02-domain-model.md]].
- **Avoid generic names**: Names like `data`, `info`, `manager`, `handler` are too vague. Be specific.

### Python (Backend)

**Files and Modules**:
- Use `snake_case` for filenames: `tenant_repository.py`, `create_agent_use_case.py`
- Use `__init__.py` to expose public module APIs

**Classes**:
- Use `PascalCase` for class names: `TenantRepository`, `CreateAgentUseCase`
- Use descriptive names that indicate responsibility: `AgentService`, not `AgentManager`

**Functions and Methods**:
- Use `snake_case` for function names: `create_tenant()`, `get_agent_by_id()`
- Use verb-noun format: `validate_input()`, `format_response()`, `retrieve_knowledge()`

**Variables**:
- Use `snake_case` for variables: `tenant_id`, `agent_name`, `knowledge_chunks`
- Use descriptive names: `conversation_history`, not `ch`

**Constants**:
- Use `UPPER_SNAKE_CASE` for constants: `MAX_CHUNK_SIZE`, `DEFAULT_EMBEDDING_MODEL`

**Type Hints**:
- Always use type hints for function signatures and class attributes
- Use explicit types, avoid `Any` unless absolutely necessary
- Use `Optional[T]` for nullable values
- Example:
  ```python
  def get_agent_by_id(agent_id: str, tenant_id: str) -> Optional[Agent]:
      pass
  ```

### TypeScript (Frontend)

**Files and Modules**:
- Use `kebab-case` for filenames: `agent-list.tsx`, `knowledge-upload.tsx`
- Use `index.ts` to expose public module APIs

**Components**:
- Use `PascalCase` for component names: `AgentList`, `KnowledgeUpload`
- Use descriptive names that indicate purpose: `ConversationHistory`, not `ChatBox`

**Functions and Variables**:
- Use `camelCase` for functions and variables: `createAgent()`, `agentName`, `conversationHistory`
- Use verb-noun format for functions: `validateInput()`, `formatResponse()`

**Types and Interfaces**:
- Use `PascalCase` for types and interfaces: `Agent`, `ConversationMessage`, `KnowledgeDocument`
- Prefix interfaces with `I` only when distinguishing from a class of the same name (avoid when possible)

**Constants**:
- Use `UPPER_SNAKE_CASE` for constants: `MAX_UPLOAD_SIZE`, `API_BASE_URL`

---

## Code Organization

### Function Structure

**Keep functions short**: A function should do one thing well. If a function exceeds 30-50 lines, consider splitting it.

**Function signature clarity**:
- Parameters should be explicit and well-named
- Use type hints (Python) or type annotations (TypeScript)
- Limit parameter count (prefer 3-5 parameters max; use objects for more)

**Return values**:
- Functions should have predictable return types
- Avoid returning different types based on conditions (use union types explicitly)
- Return early to avoid deep nesting

Example (Python):
```python
def create_agent(
    tenant_id: str,
    name: str,
    instructions: str,
    knowledge_base_config: KnowledgeBaseConfig
) -> Agent:
    # Validate inputs
    if not tenant_id or not name:
        raise ValueError("tenant_id and name are required")
    
    # Create agent
    agent = Agent(tenant_id=tenant_id, name=name, instructions=instructions)
    
    # Initialize knowledge base
    agent.knowledge_base = create_knowledge_base(agent.id, knowledge_base_config)
    
    return agent
```


### Class Structure

**Single Responsibility**: Each class should have one clear purpose.

**Composition over Inheritance**: Favor composition and delegation over deep inheritance hierarchies.

**Class organization**:
1. Class-level constants
2. Constructor / `__init__`
3. Public methods
4. Private methods
5. Static methods / class methods

Example (Python):
```python
class AgentService:
    """Service for managing AI Agent lifecycle and operations."""
    
    def __init__(self, agent_repository: AgentRepository, knowledge_service: KnowledgeService):
        self._agent_repository = agent_repository
        self._knowledge_service = knowledge_service
    
    def create_agent(self, tenant_id: str, name: str, instructions: str) -> Agent:
        """Create a new AI Agent for the specified tenant."""
        agent = Agent(tenant_id=tenant_id, name=name, instructions=instructions)
        self._agent_repository.save(agent)
        self._knowledge_service.initialize_knowledge_base(agent.id)
        return agent
    
    def _validate_agent_data(self, name: str, instructions: str) -> None:
        """Validate agent creation data."""
        if not name or not instructions:
            raise ValueError("name and instructions are required")
```


### File Organization

**One primary class per file**: Each file should contain one primary class or a group of closely related functions.

**Import organization** (Python):
1. Standard library imports
2. Third-party imports
3. Local application imports
4. Separate groups with a blank line

Example:
```python
import os
from typing import Optional, List
from datetime import datetime

from fastapi import HTTPException
from pydantic import BaseModel

from app.domain.entities.agent import Agent
from app.domain.repositories.agent_repository import AgentRepository
from app.core.auth.tenant_context import TenantContext
```

**Import organization** (TypeScript):
1. React and Next.js imports
2. Third-party library imports
3. Local component imports
4. Type imports
5. Utility imports

---

## Error Handling

### General Principles

**Fail fast**: Detect and raise errors as early as possible. Validate inputs at system boundaries.

**Be explicit**: Raise specific exceptions with clear messages. Avoid generic exceptions like `Exception` or `Error`.

**Never silently ignore errors**: Catch exceptions only when you can handle them meaningfully. Log and re-raise if unsure.

**User-facing vs internal errors**: Distinguish between errors for end users (clear, actionable messages) and internal errors (detailed diagnostic information).

### Python Error Handling

**Define domain-specific exceptions**:
```python
class DomainException(Exception):
    """Base exception for domain-level errors."""
    pass

class TenantNotFoundException(DomainException):
    """Raised when a tenant is not found."""
    pass

class AgentNotFoundException(DomainException):
    """Raised when an agent is not found."""
    pass

class KnowledgeRetrievalException(DomainException):
    """Raised when knowledge retrieval fails."""
    pass
```

**Raise exceptions with context**:
```python
def get_agent_by_id(agent_id: str, tenant_id: str) -> Agent:
    agent = self._repository.find_by_id(agent_id)
    if not agent:
        raise AgentNotFoundException(f"Agent {agent_id} not found for tenant {tenant_id}")
    if agent.tenant_id != tenant_id:
        raise UnauthorizedAccessException(f"Agent {agent_id} does not belong to tenant {tenant_id}")
    return agent
```

**Handle exceptions at appropriate layers**:
- **Domain Layer**: Raise domain-specific exceptions
- **Application Layer**: Catch domain exceptions, add context, coordinate recovery
- **Presentation Layer**: Catch application/domain exceptions, translate to HTTP responses

Example:
```python
# Presentation Layer
@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, tenant_context: TenantContext):
    try:
        agent = agent_service.get_agent_by_id(agent_id, tenant_context.tenant_id)
        return AgentResponse.from_entity(agent)
    except AgentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnauthorizedAccessException as e:
        raise HTTPException(status_code=403, detail=str(e))
```

### TypeScript Error Handling

**Use custom error classes**:
```typescript
class ApiError extends Error {
  constructor(public statusCode: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

class AgentNotFoundError extends ApiError {
  constructor(agentId: string) {
    super(404, `Agent ${agentId} not found`);
    this.name = 'AgentNotFoundError';
  }
}
```

**Handle errors in async operations**:
```typescript
async function fetchAgent(agentId: string): Promise<Agent> {
  try {
    const response = await fetch(`/api/agents/${agentId}`);
    if (!response.ok) {
      throw new AgentNotFoundError(agentId);
    }
    return await response.json();
  } catch (error) {
    if (error instanceof AgentNotFoundError) {
      throw error;
    }
    throw new ApiError(500, 'Failed to fetch agent');
  }
}
```

---

## Configuration Rules

### Environment Variables

**Use the MAAP_ prefix for all environment variables**: All platform-specific configuration variables must use the `MAAP_` (Modern AI Agent Platform) prefix to avoid conflicts with system or library variables.

**Examples**:
```bash
MAAP_DATABASE_URL=postgresql://localhost/maap
MAAP_AI_PROVIDER=openai
MAAP_AI_API_KEY=sk-...
MAAP_EMBEDDING_MODEL=text-embedding-3-small
MAAP_LOG_LEVEL=INFO
MAAP_SECRET_KEY=...
MAAP_FRONTEND_URL=http://localhost:3000
```

### Configuration Management

**Centralize configuration**: Define all configuration in a single module. Never scatter configuration across the codebase.

**Validate configuration at startup**: Fail fast if required configuration is missing or invalid.

**Use typed configuration**:
```python
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    """Application configuration."""
    
    maap_database_url: str
    maap_ai_provider: str
    maap_ai_api_key: str
    maap_embedding_model: str = "text-embedding-3-small"
    maap_log_level: str = "INFO"
    maap_secret_key: str
    
    @validator("maap_ai_provider")
    def validate_ai_provider(cls, v):
        allowed = ["openai", "anthropic", "cohere"]
        if v not in allowed:
            raise ValueError(f"AI provider must be one of {allowed}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

**Never hardcode secrets**: Use environment variables for secrets, API keys, and sensitive configuration. Never commit secrets to version control.

**Provide sensible defaults**: Configuration should have reasonable default values for non-sensitive settings.


---

## Multi-Tenant Coding Rules

Multi-tenancy is non-negotiable. Every operation must respect tenant boundaries. These rules apply to all code that touches tenant data.

### Tenant Context is Mandatory

**Never infer tenant context**: Tenant ID must be explicitly provided for every operation that accesses tenant data. Never derive, assume, or infer tenant context.

**Establish tenant context at entry points**: Extract tenant ID from authentication tokens at API boundaries. Propagate tenant context throughout the request lifecycle.

**Pass tenant context explicitly**:
```python
# CORRECT: Explicit tenant context
def get_agents(tenant_id: str) -> List[Agent]:
    return agent_repository.find_by_tenant(tenant_id)

# WRONG: No tenant context
def get_agents() -> List[Agent]:
    return agent_repository.find_all()  # This would return all agents across all tenants!
```

### Tenant Isolation in Queries

**Always scope queries by tenant ID**: Every database query that accesses tenant data must filter by tenant ID.

```python
# CORRECT: Scoped query
def find_agents_by_tenant(tenant_id: str) -> List[Agent]:
    return db.query(Agent).filter(Agent.tenant_id == tenant_id).all()

# WRONG: Unscoped query
def find_all_agents() -> List[Agent]:
    return db.query(Agent).all()  # Cross-tenant data leak!
```

### Agent Isolation in Queries

**Scope knowledge retrieval by tenant and agent**: When retrieving knowledge, always filter by both tenant ID and agent ID.

```python
# CORRECT: Scoped by tenant and agent
def retrieve_knowledge(tenant_id: str, agent_id: str, query: str) -> List[KnowledgeChunk]:
    return knowledge_repository.search(
        tenant_id=tenant_id,
        agent_id=agent_id,
        query=query
    )

# WRONG: Missing agent scope
def retrieve_knowledge(tenant_id: str, query: str) -> List[KnowledgeChunk]:
    return knowledge_repository.search(tenant_id=tenant_id, query=query)
    # This could return knowledge from other agents in the same tenant!
```

### Validate Tenant Ownership

**Verify tenant ownership before operations**: When accessing a resource by ID, verify that it belongs to the requesting tenant.

```python
def get_agent_by_id(agent_id: str, tenant_id: str) -> Agent:
    agent = agent_repository.find_by_id(agent_id)
    if not agent:
        raise AgentNotFoundException(f"Agent {agent_id} not found")
    if agent.tenant_id != tenant_id:
        raise UnauthorizedAccessException(
            f"Agent {agent_id} does not belong to tenant {tenant_id}"
        )
    return agent
```

### No Cross-Tenant Operations

**Never perform cross-tenant operations**: No function should access or modify data from multiple tenants simultaneously.

```python
# WRONG: Cross-tenant operation
def get_all_agents_across_tenants() -> List[Agent]:
    return agent_repository.find_all()  # Violates tenant isolation!

# WRONG: Aggregating across tenants
def count_total_agents() -> int:
    return agent_repository.count_all()  # Platform-wide count violates isolation!
```

**Platform-level operations are exceptions**: Only Platform Administrators performing system monitoring or maintenance may access cross-tenant data. These operations must be explicitly marked and logged.

### Tenant Context Propagation

**Propagate tenant context through the call stack**: Tenant context established at the entry point must flow through all layers.

```python
# API Layer: Establish tenant context
@router.post("/agents")
async def create_agent(request: CreateAgentRequest, tenant_context: TenantContext):
    return agent_service.create_agent(
        tenant_id=tenant_context.tenant_id,
        name=request.name,
        instructions=request.instructions
    )

# Application Layer: Pass tenant context
def create_agent(tenant_id: str, name: str, instructions: str) -> Agent:
    agent = Agent(tenant_id=tenant_id, name=name, instructions=instructions)
    self._repository.save(agent)
    return agent
```


---

## Documentation Standards

### Code Comments

**Use comments sparingly**: Code should be self-explanatory. Use comments only when code alone cannot convey intent or reasoning.

**When to comment**:
- Complex algorithms or non-obvious logic
- Business rules that are not immediately clear
- Workarounds for external library limitations
- Security or performance considerations
- References to requirements or specifications

**When NOT to comment**:
- Obvious code (`i += 1  # increment i`)
- Redundant information already in the code
- Outdated or inaccurate information

**Good comments**:
```python
# Calculate similarity using cosine distance
# Lower distance = higher similarity (range 0-2)
distance = 1 - cosine_similarity(embedding1, embedding2)

# Chunk size is limited to 512 tokens to fit within embedding model limits
# See: https://platform.openai.com/docs/guides/embeddings
MAX_CHUNK_SIZE = 512
```

### Docstrings

**Use docstrings for all public functions, classes, and modules**: Docstrings explain what the code does, not how it works.

**Python docstring format** (Google style):
```python
def retrieve_knowledge(tenant_id: str, agent_id: str, query: str, max_results: int = 5) -> List[KnowledgeChunk]:
    """Retrieve relevant knowledge chunks for a given query.
    
    Performs semantic search within the agent's knowledge base to find
    the most relevant chunks. Results are scoped by tenant and agent.
    
    Args:
        tenant_id: The tenant ID owning the agent.
        agent_id: The agent ID whose knowledge base to search.
        query: The search query text.
        max_results: Maximum number of results to return. Defaults to 5.
    
    Returns:
        List of knowledge chunks ordered by relevance (highest first).
    
    Raises:
        AgentNotFoundException: If the agent does not exist.
        KnowledgeRetrievalException: If retrieval fails due to infrastructure issues.
    """
    pass
```

**TypeScript JSDoc format**:
```typescript
/**
 * Fetch an agent by ID for the authenticated tenant.
 *
 * @param agentId - The unique identifier of the agent
 * @returns Promise resolving to the agent details
 * @throws {AgentNotFoundError} If the agent does not exist
 * @throws {ApiError} If the request fails
 */
async function fetchAgent(agentId: string): Promise<Agent> {
  // Implementation
}
```


### TODO Comments

**Use TODO comments for known issues or future work**:
```python
# TODO: Implement caching for knowledge retrieval to improve performance
# TODO: Add support for multiple embedding models
# FIXME: This workaround is needed due to a bug in the AI provider library
```

**Format**: `TODO: description` or `FIXME: description`

**Avoid**: Generic TODOs without context or owner. Always provide enough detail for someone else to understand.

---

## Performance Guidelines

### General Rules

**Measure before optimizing**: Don't optimize based on assumptions. Profile and measure actual performance. Optimize only when measurements indicate a problem.

**Optimize for clarity first**: Write clear, correct code first. Optimize only when performance is inadequate.

**Document performance assumptions**: If code makes performance assumptions (cache hit rates, query limits, response times), document them.

### Database Performance

**Use indexes for tenant_id and frequently queried fields**: Tenant ID should be indexed on every table containing tenant data.

**Avoid N+1 queries**: Use joins or batch queries instead of executing queries in loops.

```python
# WRONG: N+1 query
agents = agent_repository.find_by_tenant(tenant_id)
for agent in agents:
    agent.knowledge_base = knowledge_repository.find_by_agent(agent.id)  # N queries!

# CORRECT: Batch query
agents = agent_repository.find_by_tenant_with_knowledge(tenant_id)  # 1 query
```

**Limit result sets**: Always use pagination or limits when fetching lists of entities.

```python
# CORRECT: Paginated query
def get_agents(tenant_id: str, page: int = 1, page_size: int = 20) -> List[Agent]:
    offset = (page - 1) * page_size
    return agent_repository.find_by_tenant(tenant_id, limit=page_size, offset=offset)

# WRONG: Unbounded query
def get_agents(tenant_id: str) -> List[Agent]:
    return agent_repository.find_by_tenant(tenant_id)  # Could return millions of rows!
```

### Caching

**Cache expensive operations**: Cache AI provider responses, embedding results, and frequently accessed configuration.

**Invalidate cache appropriately**: When data changes, invalidate relevant cache entries.

**Scope cache by tenant**: Cache keys must include tenant ID to prevent cross-tenant cache pollution.

```python
# Cache key format: "tenant:{tenant_id}:agent:{agent_id}:embedding:{document_id}"
cache_key = f"tenant:{tenant_id}:agent:{agent_id}:embedding:{document_id}"
```

### API Calls

**Batch AI provider requests when possible**: Reduce API calls by batching embedding generation.

**Implement retry logic with exponential backoff**: External API calls should retry on transient failures.

**Set reasonable timeouts**: Never allow unbounded waits on external services.


---

## Code Review Checklist

Use this checklist when reviewing code. Every item must be verified before approving changes.

### Correctness

- [ ] Code implements the specified requirement correctly
- [ ] Business logic follows domain model rules
- [ ] Edge cases are handled appropriately
- [ ] Error conditions are handled correctly

### Multi-Tenancy

- [ ] Tenant context is established and propagated correctly
- [ ] All queries are scoped by tenant ID (and agent ID when applicable)
- [ ] Tenant ownership is validated before operations
- [ ] No cross-tenant data access is possible
- [ ] Agent isolation is enforced for knowledge operations

### Code Quality

- [ ] Functions and classes have single, clear responsibilities
- [ ] Names are descriptive and follow naming conventions
- [ ] Code is readable and self-explanatory
- [ ] No unnecessary complexity or over-engineering
- [ ] No code duplication without justification

### Error Handling

- [ ] Exceptions are specific and meaningful
- [ ] Error messages are clear and actionable
- [ ] Errors are handled at appropriate layers
- [ ] No silent error suppression


### Configuration

- [ ] Configuration uses MAAP_ prefix for environment variables
- [ ] No hardcoded secrets or API keys
- [ ] Configuration is validated at startup
- [ ] Sensible defaults are provided where appropriate

### Testing

- [ ] Unit tests exist for new business logic
- [ ] Tests cover edge cases and error conditions
- [ ] Tests are independent and repeatable
- [ ] Test names clearly describe what is being tested
- [ ] Multi-tenant isolation is tested

### Documentation

- [ ] Public functions and classes have docstrings
- [ ] Complex logic is explained with comments
- [ ] API changes are documented
- [ ] Breaking changes are clearly marked

### Performance

- [ ] Database queries use appropriate indexes
- [ ] No N+1 query patterns
- [ ] Result sets are bounded or paginated
- [ ] External API calls have timeouts and retry logic

### Security

- [ ] Input validation at API boundaries
- [ ] Authentication and authorization enforced
- [ ] No SQL injection vulnerabilities
- [ ] No sensitive data in logs or error messages


---

## Common Anti-Patterns

These patterns are prohibited. They violate architectural principles, create maintenance problems, or introduce security risks.

### God Classes

**Problem**: A single class that does too many things.

**Example**:
```python
# WRONG: God class
class AgentManager:
    def create_agent(self, ...): pass
    def delete_agent(self, ...): pass
    def upload_document(self, ...): pass
    def process_document(self, ...): pass
    def generate_embedding(self, ...): pass
    def search_knowledge(self, ...): pass
    def generate_response(self, ...): pass
    def send_notification(self, ...): pass
```

**Solution**: Split into focused classes with single responsibilities (AgentService, KnowledgeService, EmbeddingService, RAGPipeline).

### Implicit Tenant Context

**Problem**: Inferring tenant context from globals, thread locals, or ambient state.

**Example**:
```python
# WRONG: Implicit tenant context
current_tenant = get_current_tenant()  # Where does this come from?
agents = agent_repository.find_by_tenant(current_tenant)
```

**Solution**: Pass tenant context explicitly through function parameters.


### Anemic Domain Model

**Problem**: Domain entities with no behavior, only getters and setters.

**Example**:
```python
# WRONG: Anemic domain model
class Agent:
    def __init__(self):
        self.id = None
        self.name = None
        self.tenant_id = None

# Business logic scattered in services
def validate_agent_name(agent):
    if not agent.name or len(agent.name) < 3:
        raise ValueError("Agent name too short")
```

**Solution**: Put behavior in domain entities where it belongs.

```python
# CORRECT: Rich domain model
class Agent:
    def __init__(self, tenant_id: str, name: str):
        self._validate_name(name)
        self.tenant_id = tenant_id
        self.name = name
    
    def _validate_name(self, name: str) -> None:
        if not name or len(name) < 3:
            raise ValueError("Agent name must be at least 3 characters")
```

### Magic Numbers and Strings

**Problem**: Hardcoded values without explanation or symbolic names.

**Example**:
```python
# WRONG: Magic numbers
if len(chunk) > 512:
    raise ValueError("Chunk too large")
```

**Solution**: Use named constants with clear meaning.

```python
# CORRECT: Named constant
MAX_CHUNK_SIZE_TOKENS = 512  # OpenAI embedding model limit

if len(chunk) > MAX_CHUNK_SIZE_TOKENS:
    raise ValueError(f"Chunk exceeds maximum size of {MAX_CHUNK_SIZE_TOKENS} tokens")
```


### Circular Dependencies

**Problem**: Module A imports Module B, and Module B imports Module A.

**Example**:
```python
# file: agent_service.py
from knowledge_service import KnowledgeService

# file: knowledge_service.py
from agent_service import AgentService  # Circular dependency!
```

**Solution**: Restructure dependencies. Use dependency inversion or extract shared interfaces.

### Leaky Abstractions

**Problem**: Implementation details leak through abstractions.

**Example**:
```python
# WRONG: Database-specific exception leaking to application layer
def get_agent(agent_id: str) -> Agent:
    try:
        return db.query(Agent).filter_by(id=agent_id).one()
    except NoResultFound:  # SQLAlchemy-specific exception!
        raise
```

**Solution**: Translate infrastructure exceptions to domain exceptions at boundaries.

```python
# CORRECT: Domain exception
def get_agent(agent_id: str) -> Agent:
    try:
        return db.query(Agent).filter_by(id=agent_id).one()
    except NoResultFound:
        raise AgentNotFoundException(f"Agent {agent_id} not found")
```


### Silent Failures

**Problem**: Catching exceptions without handling or logging them.

**Example**:
```python
# WRONG: Silent failure
try:
    result = external_api.call()
except Exception:
    pass  # Error is silently ignored!
```

**Solution**: Log and re-raise, or handle meaningfully.

```python
# CORRECT: Explicit error handling
try:
    result = external_api.call()
except APIException as e:
    logger.error(f"External API call failed: {e}")
    raise ExternalServiceException("Failed to retrieve data from external service") from e
```

### Hardcoded Business Logic

**Problem**: Business rules or tenant-specific logic hardcoded in the platform.

**Example**:
```python
# WRONG: Hardcoded business logic
if tenant_id == "acme-corp":
    return special_agent_behavior()
```

**Solution**: Drive behavior through configuration (Agent Instructions, System Prompts).

### Premature Optimization

**Problem**: Optimizing code before identifying actual performance problems.

**Example**:
```python
# WRONG: Complex caching without measuring need
@lru_cache(maxsize=10000)
@memoize
def simple_calculation(x: int) -> int:
    return x + 1  # Overkill!
```

**Solution**: Write clear code first. Optimize only when measurements indicate a problem.


---

## Language-Specific Standards

### Python Standards

**Python version**: Python 3.12 or later

**Type hints**: Always use type hints for function signatures, class attributes, and return values.

**Formatting**: Use `black` for code formatting with default settings.

**Linting**: Use `ruff` or `flake8` for linting.

**Import sorting**: Use `isort` to organize imports.

**Docstrings**: Follow Google docstring style.

**Async/await**: Use async/await for I/O-bound operations (database queries, external API calls).

**Context managers**: Use context managers (`with` statements) for resource management.

**List comprehensions**: Prefer list comprehensions over `map()` and `filter()` for simple transformations.

**F-strings**: Use f-strings for string formatting.

```python
# CORRECT: f-string
message = f"Agent {agent_id} created for tenant {tenant_id}"

# WRONG: Old-style formatting
message = "Agent %s created for tenant %s" % (agent_id, tenant_id)
```

### TypeScript Standards

**TypeScript version**: Latest stable TypeScript

**Type safety**: Enable strict mode in `tsconfig.json`.

**Formatting**: Use `prettier` for code formatting.

**Linting**: Use ESLint with TypeScript rules.

**Prefer `const`**: Use `const` by default, `let` only when reassignment is needed. Never use `var`.

**Arrow functions**: Prefer arrow functions for callbacks and inline functions.

**Async/await**: Use async/await over promise chains for readability.

**Template literals**: Use template literals for string interpolation.

```typescript
// CORRECT: Template literal
const message = `Agent ${agentId} created for tenant ${tenantId}`;

// WRONG: String concatenation
const message = "Agent " + agentId + " created for tenant " + tenantId;
```

**Optional chaining**: Use optional chaining (`?.`) for accessing potentially undefined properties.

```typescript
// CORRECT: Optional chaining
const agentName = agent?.name ?? 'Unknown';

// WRONG: Manual null checks
const agentName = agent && agent.name ? agent.name : 'Unknown';
```

---

## Dependency Injection Rules

Dependency injection improves testability, flexibility, and maintainability by inverting control and making dependencies explicit. These rules ensure proper dependency management throughout the codebase.

### Prefer Constructor Injection

**Always inject dependencies through constructors**: Dependencies should be provided when objects are created, making them explicit and immutable.

```python
# CORRECT: Constructor injection
class AgentService:
    def __init__(
        self, 
        agent_repository: AgentRepository,
        knowledge_service: KnowledgeService,
        ai_client: AIClient
    ):
        self._agent_repository = agent_repository
        self._knowledge_service = knowledge_service
        self._ai_client = ai_client
    
    def create_agent(self, tenant_id: str, name: str) -> Agent:
        agent = Agent(tenant_id=tenant_id, name=name)
        self._agent_repository.save(agent)
        self._knowledge_service.initialize_knowledge_base(agent.id)
        return agent

# WRONG: Creating dependencies internally
class AgentService:
    def __init__(self):
        self._agent_repository = AgentRepository()  # Hidden dependency!
        self._knowledge_service = KnowledgeService()  # Tight coupling!
```

### Avoid Service Creation Inside Services

**Never instantiate services within services**: Service creation should happen at the application boundary (dependency injection container or main module).

```python
# WRONG: Service creating another service
class RAGPipeline:
    def process(self, query: str) -> str:
        embedding_service = EmbeddingService()  # Don't create services here!
        knowledge_service = KnowledgeService()
        # ...

# CORRECT: Dependencies injected
class RAGPipeline:
    def __init__(
        self, 
        embedding_service: EmbeddingService,
        knowledge_service: KnowledgeService
    ):
        self._embedding_service = embedding_service
        self._knowledge_service = knowledge_service
```

### Avoid Global State

**Never use global variables for dependencies**: Global state makes testing difficult, creates hidden dependencies, and causes unpredictable behavior.

```python
# WRONG: Global state
_ai_client = None

def get_ai_client():
    global _ai_client
    if _ai_client is None:
        _ai_client = AIClient()
    return _ai_client

# CORRECT: Dependency injection
class AgentService:
    def __init__(self, ai_client: AIClient):
        self._ai_client = ai_client
```

### Avoid Singleton Patterns Unless Explicitly Required

**Use dependency injection instead of singletons**: Singletons are global state in disguise. Use dependency injection to control object lifecycle.

```python
# WRONG: Singleton pattern
class DatabaseConnection:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DatabaseConnection()
        return cls._instance

# CORRECT: Dependency injection manages lifecycle
# In main.py or dependency container:
db_connection = DatabaseConnection()
agent_repository = AgentRepository(db_connection)
agent_service = AgentService(agent_repository)
```

**Exception**: Connection pools, configuration objects, and logging infrastructure may use singleton-like patterns when managed by the framework or dependency injection container.

### Depend on Abstractions, Not Implementations

**Inject interfaces or abstract classes, not concrete implementations**: This allows substituting implementations without changing dependent code.

```python
# CORRECT: Depend on abstraction
from abc import ABC, abstractmethod

class AgentRepository(ABC):
    @abstractmethod
    def save(self, agent: Agent) -> None:
        pass
    
    @abstractmethod
    def find_by_id(self, agent_id: str) -> Optional[Agent]:
        pass

class AgentService:
    def __init__(self, agent_repository: AgentRepository):
        self._agent_repository = agent_repository  # Depends on interface

# Implementations can vary
class PostgresAgentRepository(AgentRepository):
    def save(self, agent: Agent) -> None:
        # PostgreSQL implementation
        pass

class InMemoryAgentRepository(AgentRepository):
    def save(self, agent: Agent) -> None:
        # In-memory implementation for testing
        pass
```

**TypeScript example**:
```typescript
// Define interface
interface AgentRepository {
  save(agent: Agent): Promise<void>;
  findById(agentId: string): Promise<Agent | null>;
}

// Depend on interface
class AgentService {
  constructor(private readonly agentRepository: AgentRepository) {}
  
  async createAgent(tenantId: string, name: string): Promise<Agent> {
    const agent = new Agent(tenantId, name);
    await this.agentRepository.save(agent);
    return agent;
  }
}
```

---

## API Coding Rules

API handlers are the entry point to the application. They must validate input, establish context, and translate between external and internal representations. Business logic belongs in the application layer, not in API handlers.

### Validate Input at the API Boundary

**Always validate request data at the API layer**: Never allow invalid data to enter the system. Use validation schemas to enforce data contracts.

```python
# CORRECT: Input validation with Pydantic
from pydantic import BaseModel, Field, validator

class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    instructions: str = Field(..., min_length=10, max_length=5000)
    
    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

@router.post("/agents")
async def create_agent(
    request: CreateAgentRequest, 
    tenant_context: TenantContext
) -> AgentResponse:
    # Request is validated automatically by FastAPI + Pydantic
    agent = agent_service.create_agent(
        tenant_id=tenant_context.tenant_id,
        name=request.name,
        instructions=request.instructions
    )
    return AgentResponse.from_entity(agent)
```

**TypeScript example** (Next.js API route):
```typescript
import { z } from 'zod';

const createAgentSchema = z.object({
  name: z.string().min(3).max(100),
  instructions: z.string().min(10).max(5000),
});

export async function POST(request: Request) {
  // Validate input
  const body = await request.json();
  const validatedData = createAgentSchema.parse(body);
  
  // Process request
  const agent = await agentService.createAgent(
    tenantId,
    validatedData.name,
    validatedData.instructions
  );
  
  return Response.json(agent);
}
```

### Never Place Business Logic Inside API Handlers

**API handlers should be thin**: They coordinate the request/response cycle but contain no business logic. Business logic belongs in application services or domain entities.

```python
# WRONG: Business logic in API handler
@router.post("/agents/{agent_id}/chat")
async def chat(agent_id: str, request: ChatRequest, tenant_context: TenantContext):
    # Retrieving data
    agent = agent_repository.find_by_id(agent_id)
    if agent.tenant_id != tenant_context.tenant_id:
        raise HTTPException(403)
    
    # Business logic in handler - WRONG!
    query_embedding = embedding_service.generate_embedding(request.message)
    chunks = knowledge_repository.search(agent_id, query_embedding, limit=5)
    context = "\n".join([chunk.content for chunk in chunks])
    prompt = f"Context:\n{context}\n\nUser: {request.message}\nAgent:"
    response = ai_client.generate(prompt)
    
    return {"response": response}

# CORRECT: Delegate to application service
@router.post("/agents/{agent_id}/chat")
async def chat(
    agent_id: str, 
    request: ChatRequest, 
    tenant_context: TenantContext
) -> ChatResponse:
    response = await chat_service.process_message(
        tenant_id=tenant_context.tenant_id,
        agent_id=agent_id,
        message=request.message
    )
    return ChatResponse(response=response)
```

### Use Request/Response Schemas

**Define explicit schemas for all API endpoints**: Schemas document the API contract and enable automatic validation and serialization.

```python
# Request schema
class CreateAgentRequest(BaseModel):
    name: str
    instructions: str
    model: str = "gpt-4"
    temperature: float = 0.7

# Response schema
class AgentResponse(BaseModel):
    id: str
    name: str
    instructions: str
    model: str
    temperature: float
    created_at: datetime
    
    @classmethod
    def from_entity(cls, agent: Agent) -> "AgentResponse":
        return cls(
            id=agent.id,
            name=agent.name,
            instructions=agent.instructions,
            model=agent.model,
            temperature=agent.temperature,
            created_at=agent.created_at
        )
```

### Return Consistent Response Structures

**Standardize response formats**: All API responses should follow a consistent structure for success and error cases.

```python
# Success response structure
{
    "data": { /* response data */ },
    "metadata": {
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "req_123"
    }
}

# Error response structure
{
    "error": {
        "code": "AGENT_NOT_FOUND",
        "message": "Agent with ID 'agent_123' not found",
        "details": {}
    },
    "metadata": {
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "req_124"
    }
}
```

### Translate Exceptions at the API Boundary Only

**Convert domain exceptions to HTTP responses at the API layer**: Don't let internal exceptions leak to clients. Map domain exceptions to appropriate HTTP status codes.

```python
# CORRECT: Exception translation at API boundary
@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, tenant_context: TenantContext) -> AgentResponse:
    try:
        agent = agent_service.get_agent_by_id(agent_id, tenant_context.tenant_id)
        return AgentResponse.from_entity(agent)
    except AgentNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnauthorizedAccessException as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Database Coding Rules

Database access must be isolated in repository classes. These rules ensure proper data access patterns, tenant isolation, and query performance.

### Database Access Belongs Only to Repositories

**Only repository classes should execute database queries**: Services, use cases, and API handlers must never access the database directly.

```python
# CORRECT: Database access in repository
class AgentRepository:
    def __init__(self, db: Database):
        self._db = db
    
    def find_by_tenant(self, tenant_id: str) -> List[Agent]:
        return self._db.query(Agent).filter(Agent.tenant_id == tenant_id).all()

# Application service uses repository
class AgentService:
    def __init__(self, agent_repository: AgentRepository):
        self._agent_repository = agent_repository
    
    def get_agents(self, tenant_id: str) -> List[Agent]:
        return self._agent_repository.find_by_tenant(tenant_id)

# WRONG: Service accessing database directly
class AgentService:
    def __init__(self, db: Database):
        self._db = db
    
    def get_agents(self, tenant_id: str) -> List[Agent]:
        return self._db.query(Agent).filter(Agent.tenant_id == tenant_id).all()
```

### Services Never Execute SQL Directly

**Never write raw SQL in service classes**: All database operations must go through repository methods.

```python
# WRONG: Raw SQL in service
class AgentService:
    def get_agents(self, tenant_id: str) -> List[Agent]:
        sql = "SELECT * FROM agents WHERE tenant_id = %s"
        return self._db.execute(sql, [tenant_id])  # Don't do this!

# CORRECT: Use repository method
class AgentService:
    def get_agents(self, tenant_id: str) -> List[Agent]:
        return self._agent_repository.find_by_tenant(tenant_id)
```

**Exception**: Repository classes may use raw SQL for complex queries when ORM capabilities are insufficient. Document the reasoning.

### Every Tenant-Aware Query Must Include Tenant Context

**Always filter by tenant_id when querying tenant data**: Every database query that accesses tenant-scoped entities must include a tenant_id filter.

```python
# CORRECT: Tenant-scoped query
class AgentRepository:
    def find_by_id(self, agent_id: str, tenant_id: str) -> Optional[Agent]:
        return self._db.query(Agent)\
            .filter(Agent.id == agent_id)\
            .filter(Agent.tenant_id == tenant_id)\
            .first()

# WRONG: Missing tenant filter - security vulnerability!
class AgentRepository:
    def find_by_id(self, agent_id: str) -> Optional[Agent]:
        return self._db.query(Agent)\
            .filter(Agent.id == agent_id)\
            .first()  # Could return agent from any tenant!
```

### Use Pagination for Collections

**Always paginate list queries**: Never return unbounded result sets. Use limit and offset for pagination.

```python
# CORRECT: Paginated query
class AgentRepository:
    def find_by_tenant(
        self, 
        tenant_id: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> List[Agent]:
        offset = (page - 1) * page_size
        return self._db.query(Agent)\
            .filter(Agent.tenant_id == tenant_id)\
            .limit(page_size)\
            .offset(offset)\
            .all()

# WRONG: Unbounded query
class AgentRepository:
    def find_by_tenant(self, tenant_id: str) -> List[Agent]:
        return self._db.query(Agent)\
            .filter(Agent.tenant_id == tenant_id)\
            .all()  # Could return millions of rows!
```

### Avoid N+1 Queries

**Use joins or batch queries instead of loops**: N+1 queries cause severe performance problems. Load related data in a single query when possible.

```python
# WRONG: N+1 query pattern
agents = agent_repository.find_by_tenant(tenant_id)
for agent in agents:
    agent.knowledge_base = knowledge_repository.find_by_agent(agent.id)  # N queries!

# CORRECT: Eager loading with join
class AgentRepository:
    def find_by_tenant_with_knowledge(self, tenant_id: str) -> List[Agent]:
        return self._db.query(Agent)\
            .filter(Agent.tenant_id == tenant_id)\
            .options(joinedload(Agent.knowledge_base))\
            .all()

# CORRECT: Batch query
agents = agent_repository.find_by_tenant(tenant_id)
agent_ids = [agent.id for agent in agents]
knowledge_bases = knowledge_repository.find_by_agent_ids(agent_ids)  # 1 query
knowledge_map = {kb.agent_id: kb for kb in knowledge_bases}
for agent in agents:
    agent.knowledge_base = knowledge_map.get(agent.id)
```

---

## Logging Rules

Logging is essential for debugging and monitoring, but improper logging can expose sensitive data or create security vulnerabilities. These rules ensure safe, useful logging.

### Never Log Secrets

**Never log passwords, API keys, tokens, or secrets**: Logging sensitive data creates security vulnerabilities and compliance issues.

```python
# WRONG: Logging secrets
logger.info(f"Connecting to AI provider with API key: {api_key}")  # Don't do this!
logger.debug(f"User password: {password}")  # Never log passwords!

# CORRECT: Log without secrets
logger.info("Connecting to AI provider")
logger.debug(f"User authentication attempt for user: {username}")
```

### Never Log API Keys

**Mask or omit API keys in logs**: If you must log an API key reference, mask all but the last few characters.

```python
# CORRECT: Masked API key
def mask_api_key(key: str) -> str:
    if len(key) <= 8:
        return "***"
    return f"***{key[-4:]}"

logger.info(f"Using API key: {mask_api_key(api_key)}")  # "Using API key: ***ab12"
```

### Never Log Access Tokens

**Never log OAuth tokens, JWT tokens, or session tokens**: Tokens grant access and must be treated as secrets.

```python
# WRONG: Logging access token
logger.info(f"Request authenticated with token: {access_token}")  # Security vulnerability!

# CORRECT: Log authentication status without token
logger.info(f"Request authenticated for tenant: {tenant_id}, user: {user_id}")
```

### Use Appropriate Log Levels

**Choose the correct log level for each message**:

- **DEBUG**: Detailed diagnostic information for troubleshooting. Disabled in production.
- **INFO**: General informational messages about application flow (requests, operations completed).
- **WARNING**: Potentially harmful situations or degraded behavior (retries, fallbacks).
- **ERROR**: Error events that might still allow the application to continue.
- **CRITICAL**: Severe errors that may cause the application to abort.

```python
# CORRECT: Appropriate log levels
logger.debug(f"Generating embedding for document: {document_id}")  # Diagnostic detail
logger.info(f"Agent created: {agent_id} for tenant: {tenant_id}")  # Normal operation
logger.warning(f"AI provider timeout, retrying request (attempt {retry_count})")  # Degradation
logger.error(f"Failed to retrieve knowledge for agent: {agent_id}: {error}")  # Error condition
logger.critical(f"Database connection failed, unable to serve requests")  # Critical failure
```

### Log Enough Context for Troubleshooting Without Exposing Sensitive Data

**Include identifiers, not content**: Log IDs, operation types, and status. Don't log message content, document text, or user data.

```python
# CORRECT: Log identifiers and operation details
logger.info(f"Processing chat message for agent: {agent_id}, tenant: {tenant_id}")
logger.info(f"Retrieved {len(chunks)} knowledge chunks for query")
logger.info(f"Generated response in {duration_ms}ms")

# WRONG: Logging sensitive content
logger.info(f"User message: {user_message}")  # Don't log user input!
logger.info(f"Retrieved chunks: {chunks}")  # Don't log document content!
logger.info(f"AI response: {response_text}")  # Don't log AI responses!
```

**Include tenant and agent context in all logs**: Every log message for tenant-scoped operations should include tenant_id and agent_id for filtering and debugging.

```python
# CORRECT: Structured logging with context
logger.info(
    "Knowledge retrieval completed",
    extra={
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "query_duration_ms": duration_ms,
        "result_count": len(chunks)
    }
)
```

---

## AI Coding Rules

AI integration requires special care to ensure proper separation of concerns, tenant and agent isolation, and correct retrieval-augmented generation patterns.

### Never Call AI Providers Directly from API Handlers

**API handlers must not call AI services directly**: AI integration belongs in dedicated service classes, not API routes.

```python
# WRONG: AI call in API handler
@router.post("/agents/{agent_id}/chat")
async def chat(agent_id: str, request: ChatRequest, tenant_context: TenantContext):
    # Don't call AI provider directly from handler!
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": request.message}]
    )
    return {"response": response.choices[0].message.content}

# CORRECT: Delegate to service
@router.post("/agents/{agent_id}/chat")
async def chat(
    agent_id: str, 
    request: ChatRequest, 
    tenant_context: TenantContext
) -> ChatResponse:
    response = await chat_service.process_message(
        tenant_id=tenant_context.tenant_id,
        agent_id=agent_id,
        message=request.message
    )
    return ChatResponse(response=response)
```

### AI Communication Belongs to Dedicated AI Services

**Isolate AI provider integration in dedicated services**: Create service classes that encapsulate AI provider communication, retry logic, and error handling.

```python
# CORRECT: Dedicated AI service
class AIClient:
    def __init__(self, provider: str, api_key: str):
        self._provider = provider
        self._api_key = api_key
    
    async def generate_completion(
        self, 
        messages: List[Message], 
        model: str,
        temperature: float = 0.7
    ) -> str:
        """Generate chat completion from AI provider."""
        try:
            response = await self._call_provider(messages, model, temperature)
            return response
        except ProviderTimeoutException:
            logger.warning("AI provider timeout, retrying...")
            return await self._call_provider(messages, model, temperature)
        except ProviderException as e:
            logger.error(f"AI provider error: {e}")
            raise AIGenerationException("Failed to generate AI response") from e
```

### Separate Embedding Generation from Text Generation

**Use separate services for embeddings and text generation**: These are different operations with different performance characteristics and error handling requirements.

```python
# CORRECT: Separate services
class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self, ai_client: AIClient):
        self._ai_client = ai_client
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        return await self._ai_client.create_embedding(text)

class CompletionService:
    """Service for generating text completions."""
    
    def __init__(self, ai_client: AIClient):
        self._ai_client = ai_client
    
    async def generate_completion(
        self, 
        messages: List[Message],
        model: str
    ) -> str:
        """Generate text completion from messages."""
        return await self._ai_client.generate_completion(messages, model)
```

### Always Scope Retrieval by Tenant and Agent

**Knowledge retrieval must filter by both tenant_id and agent_id**: Never retrieve knowledge across tenant or agent boundaries.

```python
# CORRECT: Scoped retrieval
class KnowledgeService:
    async def retrieve_relevant_chunks(
        self, 
        tenant_id: str,
        agent_id: str,
        query: str,
        max_results: int = 5
    ) -> List[KnowledgeChunk]:
        """Retrieve relevant knowledge chunks scoped by tenant and agent."""
        query_embedding = await self._embedding_service.generate_embedding(query)
        
        chunks = await self._knowledge_repository.search(
            tenant_id=tenant_id,  # Must filter by tenant
            agent_id=agent_id,    # Must filter by agent
            query_embedding=query_embedding,
            limit=max_results
        )
        
        return chunks

# WRONG: Missing agent scope
class KnowledgeService:
    async def retrieve_relevant_chunks(
        self, 
        tenant_id: str,
        query: str
    ) -> List[KnowledgeChunk]:
        # Missing agent_id filter - could return knowledge from other agents!
        query_embedding = await self._embedding_service.generate_embedding(query)
        return await self._knowledge_repository.search(
            tenant_id=tenant_id,
            query_embedding=query_embedding
        )
```

### Never Generate Answers Without Retrieval When Knowledge is Required

**Always perform retrieval when agent has a knowledge base**: If an agent is configured with a knowledge base, always retrieve relevant chunks before generating a response.

```python
# CORRECT: Retrieval-augmented generation
class RAGPipeline:
    async def generate_response(
        self,
        tenant_id: str,
        agent_id: str,
        message: str,
        conversation_history: List[Message]
    ) -> str:
        """Generate response using retrieval-augmented generation."""
        
        # Retrieve relevant knowledge
        chunks = await self._knowledge_service.retrieve_relevant_chunks(
            tenant_id=tenant_id,
            agent_id=agent_id,
            query=message
        )
        
        # Build context from retrieved chunks
        context = self._build_context(chunks)
        
        # Generate response with context
        messages = self._build_messages(
            agent_instructions=agent.instructions,
            context=context,
            conversation_history=conversation_history,
            user_message=message
        )
        
        return await self._completion_service.generate_completion(
            messages=messages,
            model=agent.model
        )

# WRONG: Skipping retrieval
class ChatService:
    async def generate_response(self, agent_id: str, message: str) -> str:
        # Directly generating without checking knowledge base!
        return await self._ai_client.generate_completion(message)
```

---

## Golden Rules

These are the absolute, non-negotiable rules. Violating these rules creates security vulnerabilities, data leaks, or architectural corruption.

### Never Bypass Tenant Isolation

**Every operation must respect tenant boundaries**: Never access, modify, or expose data from other tenants. Tenant isolation is a security requirement, not a suggestion.

```python
# CORRECT: Tenant-scoped operation
def get_agent(agent_id: str, tenant_id: str) -> Agent:
    agent = self._repository.find_by_id(agent_id)
    if agent.tenant_id != tenant_id:
        raise UnauthorizedAccessException("Access denied")
    return agent

# WRONG: No tenant verification - security vulnerability!
def get_agent(agent_id: str) -> Agent:
    return self._repository.find_by_id(agent_id)
```

### Never Hardcode Business Logic

**Business logic belongs in configuration or domain entities**: Never hardcode tenant-specific behavior, rules, or workflows in platform code.

```python
# WRONG: Hardcoded business logic
if tenant_id == "acme-corp":
    return special_pricing_logic()
elif tenant_id == "beta-company":
    return different_workflow()

# CORRECT: Configuration-driven behavior
pricing_config = self._config_service.get_pricing_config(tenant_id)
return self._pricing_service.calculate(pricing_config)
```

### Never Duplicate Business Rules

**Define business rules once**: If the same logic appears in multiple places, extract it to a shared location (domain entity, domain service, or application service).

```python
# WRONG: Duplicated validation
# In API handler:
if len(agent_name) < 3:
    raise ValueError("Name too short")

# In service:
if len(agent_name) < 3:
    raise ValueError("Name too short")

# CORRECT: Validation in domain entity
class Agent:
    def __init__(self, tenant_id: str, name: str):
        self._validate_name(name)
        self.name = name
    
    def _validate_name(self, name: str) -> None:
        if len(name) < 3:
            raise ValueError("Agent name must be at least 3 characters")
```

### Never Skip Validation

**Validate all input at system boundaries**: Never trust external input. Validate early and fail fast.

```python
# CORRECT: Input validation
def create_agent(tenant_id: str, name: str, instructions: str) -> Agent:
    if not tenant_id:
        raise ValueError("tenant_id is required")
    if not name or len(name) < 3:
        raise ValueError("name must be at least 3 characters")
    if not instructions:
        raise ValueError("instructions are required")
    
    return Agent(tenant_id=tenant_id, name=name, instructions=instructions)
```

### Never Skip Tests

**Write tests for all new code**: Code without tests is unverified code. Tests prevent regressions and document behavior.

```python
# Every new feature needs tests
def test_create_agent():
    agent = agent_service.create_agent(
        tenant_id="tenant_123",
        name="Test Agent",
        instructions="Test instructions"
    )
    assert agent.tenant_id == "tenant_123"
    assert agent.name == "Test Agent"

def test_create_agent_validates_name():
    with pytest.raises(ValueError, match="name must be at least 3 characters"):
        agent_service.create_agent(
            tenant_id="tenant_123",
            name="ab",
            instructions="Test instructions"
        )
```

### Never Assume Requirements

**Clarify unclear requirements before implementing**: If requirements are ambiguous, incomplete, or contradictory, ask for clarification. Don't guess.

### Always Inspect Existing Code First

**Read existing code before writing new code**: Understand existing patterns, conventions, and implementations before adding new code. Match the existing style.

### One Task, One Goal, Finish, Stop

**Focus on one task at a time**: Complete the task you're working on before moving to the next. Don't context-switch or partially implement multiple features.

**Define clear goals**: Know what "done" looks like before starting. When the goal is achieved, stop.

**Finish completely**: Don't leave tasks partially done. Complete implementation, tests, and documentation before moving on.

---

## References

- Architectural context: #[[file:03-system-architecture.md]]
- Domain terminology: #[[file:02-domain-model.md]]
- Project context: #[[file:01-project.md]]

---

## Document Boundaries

This document defines HOW code should be written. It establishes coding standards, conventions, and patterns.


**This document must never contain:**

- **Architecture**: System layers, component relationships, integration boundaries, or architectural patterns belong in #[[file:03-system-architecture.md]].
- **Business domain**: Entity definitions, business rules, lifecycle, or ubiquitous language belong in #[[file:02-domain-model.md]].
- **Project scope**: Mission, target users, current phase, or strategic objectives belong in #[[file:01-project.md]].
- **Workflow processes**: Development workflow, release processes, or team ceremonies belong in process documents.
- **Database schema**: Table definitions, column types, indexes, or query structures belong in architecture or implementation documents.
- **API specifications**: REST endpoints, HTTP methods, request/response formats belong in API documentation.
- **Deployment**: Infrastructure, container configurations, or CI/CD pipelines belong in deployment documents.

This document focuses exclusively on **code quality** (readability, maintainability), **code structure** (organization, naming), **coding patterns** (error handling, configuration), and **implementation standards** (language-specific rules, anti-patterns).

When questions arise about other topics, refer to the appropriate steering document.
