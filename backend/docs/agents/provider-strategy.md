# Provider Strategy — TX AI Lab Platform

## Overview

The TX AI Lab Platform abstracts AI capabilities behind provider-independent interfaces, enabling the platform to switch between or combine multiple AI service providers without rewriting business logic.

## Current Provider Configuration (Sprint 1)

### Generation Provider
- **Provider**: DeepSeek
- **Model**: `deepseek-v4-flash`
- **Use Case**: Text generation for agent responses
- **Interface**: `GenerationProvider` protocol in `backend/app/ai/ports.py`
- **Implementation**: `backend/app/ai/providers/deepseek.py`

### Embedding Provider
- **Provider**: Voyage AI
- **Model**: `voyage-4-large`
- **Dimension**: 1024
- **Input Types**: `document` (for ingestion), `query` (for retrieval)
- **Use Case**: Document and query vectorization
- **Interface**: `EmbeddingProvider` protocol in `backend/app/ai/ports.py`
- **Implementation**: `backend/app/ai/providers/voyage.py`

### Reranking Provider
- **Provider**: Voyage AI
- **Model**: `rerank-2.5`
- **Use Case**: Second-stage relevance refinement in RAG pipeline
- **Interface**: `RerankProvider` protocol in `backend/app/ai/ports.py`
- **Implementation**: `backend/app/ai/providers/voyage.py` (`VoyageRerankProvider`)

## Provider Abstraction Architecture

### Core Principles

1. **Interface Segregation**: Each capability (generation, embedding, reranking) has its own protocol interface.
2. **Dependency Inversion**: Business logic depends on protocols, not concrete implementations.
3. **Graceful Degradation**: Missing providers (e.g., reranking) degrade safely without blocking operation.
4. **Tenant Isolation**: Provider interfaces never expose tenant metadata to external services.

### Provider Protocols

All provider protocols are defined in `backend/app/ai/ports.py`:

```python
class GenerationProvider(Protocol):
    async def generate(self, request: GenerationRequest) -> GenerationResult: ...

class EmbeddingProvider(Protocol):
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...

class RerankProvider(Protocol):
    async def rerank(self, request: RerankRequest) -> RerankResult: ...
```

### Runtime Gateway

`CoreAIRuntime` (`backend/app/ai/runtime.py`) serves as the single entry point for all provider interactions:

```python
class CoreAIRuntime:
    def __init__(
        self,
        generation_provider: GenerationProvider,
        embedding_provider: EmbeddingProvider,
        *,
        rerank_provider: RerankProvider | None = None,
    ) -> None: ...

    async def generate(self, request: GenerationRequest) -> GenerationResult: ...
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult: ...
    async def rerank(self, request: RerankRequest) -> RerankResult: ...
```

**Benefits:**
- Business logic never imports provider implementations directly
- Provider configuration centralized at composition root
- Testing uses stub providers without mocking
- Provider replacement requires zero changes to business logic

## Provider Coupling Assessment

### ✅ Generation (DeepSeek)
- **Status**: Fully abstracted
- **Coupling**: None — business logic only depends on `GenerationProvider` protocol
- **Switchability**: High — any OpenAI-compatible provider can implement the interface
- **Current Implementation**: Uses LangChain's `ChatDeepSeek` wrapper

### ✅ Embedding (Voyage)
- **Status**: Fully abstracted
- **Coupling**: None — business logic only depends on `EmbeddingProvider` protocol
- **Switchability**: High — vector dimension is configurable via Settings
- **Current Implementation**: Direct HTTP API integration with retry logic

### ✅ Reranking (Voyage)
- **Status**: Fully abstracted (as of Sprint 1)
- **Coupling**: None — `RetrievalService` depends on `RerankProvider` protocol
- **Switchability**: High — graceful fallback to pgvector ranking when provider unavailable
- **Current Implementation**: Direct HTTP API integration

## Adding a New Provider

### Example: Adding Anthropic as Generation Provider

1. **Create Implementation** (`backend/app/ai/providers/anthropic.py`):

```python
from backend.app.ai.ports import GenerationProvider
from backend.app.ai.contracts import GenerationRequest, GenerationResult

class AnthropicGenerationProvider(GenerationProvider):
    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.anthropic_api_key
        self._model = settings.anthropic_model

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        # Implementation here
        ...
```

2. **Update Configuration** (`backend/app/core/config.py`):

```python
class Settings(BaseSettings):
    # Existing...
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
```

3. **Update Composition Root** (dependency injection setup):

```python
# Choose provider based on configuration
if settings.generation_provider == "deepseek":
    generation_provider = DeepSeekGenerationProvider(settings)
elif settings.generation_provider == "anthropic":
    generation_provider = AnthropicGenerationProvider(settings)

runtime = CoreAIRuntime(
    generation_provider=generation_provider,
    embedding_provider=embedding_provider,
    rerank_provider=rerank_provider,
)
```

**No changes required to:**
- `ChatWorkflow`
- `RetrievalService`
- Domain models
- API routes
- Tests (business logic tests continue using stub providers)

## Provider Selection Strategy (Future)

The Sprint 1 requirement document specifies model routing considerations for future implementation:

### Routing Factors (Design Only — Not Implemented)
- **Quality**: Model accuracy/capability for specific tasks
- **Latency**: Response time requirements
- **Cost**: Token pricing and budget constraints
- **Availability**: Provider uptime and geographic proximity
- **Data Classification**: Sensitive data routing restrictions
- **Tenant Policy**: Per-tenant provider preferences

### ModelPolicy Boundary (Sprint 1)

For Sprint 1, we document the *boundary* without implementing speculative routing:

```python
# Future interface (documented, not implemented)
class ModelPolicy(Protocol):
    async def select_generation_provider(
        self,
        context: RuntimeContext,
        requirements: RoutingRequirements,
    ) -> GenerationProvider: ...
```

**Current Behavior**: Single provider selected at startup via Settings.

**Future Behavior**: `ModelPolicy` implementation could:
- Route by tenant tier (free → fast model, paid → quality model)
- Fall back on provider failure
- Load balance across multiple provider instances
- Route based on data classification (PII → on-prem model)

## Provider Failure Behavior

### Generation Provider Failure
- **Behavior**: `ChatWorkflow` catches exception, returns fallback message
- **User Impact**: Receives contact message configured in Agent
- **Telemetry**: Failure logged with `answer_status: "temporarily_unavailable"`

### Embedding Provider Failure
- **Behavior**: `RetrievalService` raises `EmbeddingError`
- **User Impact**: Same as generation failure (knowledge temporarily unavailable)
- **Degradation**: No fallback (embedding required for RAG)

### Reranking Provider Failure
- **Behavior**: `RetrievalService` falls back to pgvector similarity ranking
- **User Impact**: Slightly reduced answer quality (still functional)
- **Degradation**: Graceful — uses already-tenant-filtered pgvector candidates

## Security & Tenant Isolation

### Provider Data Transmission Rules

1. **Generation Provider** (DeepSeek):
   - Receives: system_prompt, conversation history, user query
   - Does NOT receive: tenant_id, agent_id, internal IDs
   - Justification: Prompt content is tenant-configured and necessary for generation

2. **Embedding Provider** (Voyage):
   - Receives: document text OR query text
   - Does NOT receive: tenant_id, agent_id, source metadata
   - Justification: Text must be embedded; metadata stays internal

3. **Reranking Provider** (Voyage):
   - Receives: query string, candidate document texts
   - Does NOT receive: tenant_id, agent_id, similarity scores, chunk IDs
   - Justification: Reranking requires text only; all filtering already done

**Enforcement:**
- Repository methods enforce tenant filtering BEFORE provider calls
- Provider request DTOs do not include tenant fields
- Tests verify tenant isolation at repository boundary

## Testing Strategy

### Provider Interface Tests
- Each provider implementation has dedicated tests (e.g., `test_voyage_provider.py`)
- Tests verify: retry logic, error handling, dimension validation, API contract

### Business Logic Tests
- Use **stub providers** (simple in-memory implementations)
- Test business logic without external API calls
- Example: `test_chat_workflow.py` uses stubs, never calls DeepSeek/Voyage

### Integration Tests
- Verify provider composition at startup
- Test actual provider calls in controlled environment
- Example: `test_pipeline_integration.py` tests full ingestion → retrieval flow

## Configuration Reference

All provider configuration lives in `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    # DeepSeek (Generation)
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: AnyHttpUrl = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_timeout_seconds: float = 30.0
    deepseek_max_retries: int = 2

    # Voyage (Embedding + Reranking)
    voyage_api_key: SecretStr | None = None
    voyage_base_url: AnyHttpUrl = "https://api.voyageai.com/v1"
    voyage_model: str = "voyage-4-large"
    voyage_rerank_model: str = "rerank-2.5"
    voyage_timeout_seconds: float = 30.0
    voyage_max_retries: int = 2

    # Retrieval
    retrieval_candidate_count: int = 20  # pgvector first-stage
    retrieval_final_count: int = 5       # After reranking
```

## Future Provider Roadmap (Post-Sprint 1)

### Planned Additions
- **OpenAI GPT-4** as alternative generation provider
- **Cohere Rerank** as alternative reranking provider
- **On-Premise Embedding** for sensitive data tenants

### Planned Features
- **Multi-Provider Routing**: ModelPolicy implementation
- **Provider Fallback**: Automatic failover on provider unavailability
- **A/B Testing**: Compare provider performance via Evaluation Platform
- **Cost Tracking**: Per-provider token usage and estimated cost

## References

- Provider Interfaces: `backend/app/ai/ports.py`
- Current Implementations: `backend/app/ai/providers/`
- Runtime Gateway: `backend/app/ai/runtime.py`
- Configuration: `backend/app/core/config.py`
- Sprint 1 Requirements: `AGENT_RUNTIME_EVALUATION_MANAGEMENT_ALIGNED.md`
