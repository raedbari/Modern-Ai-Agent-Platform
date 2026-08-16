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

Platform capabilities and Athkachatbots product capabilities exist, and their
logical ownership boundaries are now documented in
`product-platform-boundaries.md`. The repository has also added contract,
tenant-isolation, provider-boundary, and end-to-end tests around important
flows.

The physical structure still mixes product, shared-platform, knowledge, and
agent-runtime concerns across technical-layer folders. The documented
boundaries are therefore an architectural direction and ownership model, not
a claim that the code has already been fully modularized.

The goal is NOT a rewrite.

The next steps are to obtain Architecture v1.0 approval, protect the agreed
boundaries incrementally, and add the governance, telemetry, evaluation, and
operational evidence required for a measured pilot. Code should move only
when doing so improves an approved boundary without disrupting working pilot
functionality.

## Current Maturity Limits

- Architecture v1.0 is proposed and is not yet management-approved.
- Knowledge replacement is technically safe, but the target approval,
  classification, retention, and version-governance model is not implemented.
- Evaluation is an initial deterministic foundation, not a complete RAG
  evaluation platform.
- Upload storage is a local filesystem volume suitable only for the current
  pilot implementation; it is not production object storage.
- Health checks and application logs exist, but complete AI telemetry, cost
  measurement, backup/restore evidence, and production SLOs do not.
- DeepSeek and Voyage are active provider implementations. Ollama is legacy
  only and is not part of the target architecture.
- The current hosting topology is a controlled-pilot candidate, not an
  approved production topology.
