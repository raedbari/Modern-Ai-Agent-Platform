# TX AI Lab - Current Architecture State

## Repository Model

The system currently runs as a single repository and a single backend application.

Architecture style:

- Modular Monolith
- FastAPI backend
- PostgreSQL + pgvector
- Redis
- Background ingestion worker
- Docker Compose
- Alembic migrations

No microservices are currently required.

## Current Backend Areas

The backend is primarily organized by technical layers:

backend/app/
- ai/
- api/
- auth/
- core/
- db/
- domain/
- evaluation/
- infrastructure/
- operations/
- services/
- workers/

## Existing Platform Capabilities

### Knowledge

- Knowledge Bases
- Documents
- Chunking
- Document ingestion
- Embeddings
- pgvector retrieval
- Knowledge jobs
- Tenant-scoped retrieval

### Agent Runtime

- Provider-independent generation contracts
- Embedding provider abstraction
- Rerank provider abstraction
- DeepSeek generation provider
- Voyage embedding provider
- Voyage rerank provider
- LangGraph chat workflow
- Evidence-first generation
- Required knowledge fallback
- Citations

### Evaluation

An initial evaluation module exists with:

- Evaluation cases
- Expectations
- Runner
- Reports
- Basic deterministic checks
- Latency and token measurements

It currently evaluates generation more directly than the complete RAG pipeline.

### Shared Platform

- Tenancy
- Authentication
- Authorization
- Admin authentication
- Tenant sessions
- Audit
- Database infrastructure

### Athkachatbots Product

- SaaS onboarding
- Customer-facing chatbot management
- Widget
- Conversations
- Customer portal APIs

## Current Architectural Problem

Platform capabilities and Athkachatbots product capabilities exist, but ownership boundaries are not yet formally documented.

The current structure mixes product concerns, shared platform concerns, knowledge concerns, and agent runtime concerns across technical-layer folders.

The goal is NOT a rewrite.

The next step is to define explicit ownership and contracts while keeping the Modular Monolith.
