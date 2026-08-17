# TX AI Lab - Target Architecture

## Architecture Style

TX AI Lab will remain a Modular Monolith during the pilot phase.

No microservices are required at this stage.

## Logical Platform Structure

TX AI Lab Platform
|
|-- Knowledge Platform
|-- Agent Runtime Platform
|-- Evaluation Platform
|-- Shared Platform Services
|
`-- Products
    `-- Athkachatbots

## Dependency Direction

Athkachatbots
    |
    v
Platform Domains
    |
    v
Shared Contracts / Infrastructure

Platform domains must not depend on Athkachatbots-specific code.

## Knowledge Platform Flow

Document
→ Validate
→ Parse
→ Chunk
→ Document Embedding
→ pgvector
→ Version / Activation
→ Retrieval-ready knowledge

## Agent Runtime Flow

Question
→ Tenant / Agent scope
→ Query Embedding
→ Candidate Retrieval
→ Rerank
→ Evidence Selection
→ Answerability
→ Generation
→ Citations
→ Response

## Evaluation Flow

Dataset
→ Golden Questions
→ Agent / Prompt / Knowledge Version
→ Evaluation Run
→ Metrics
→ Comparison

## Shared Platform Services

Shared capabilities include:

- Tenancy
- Authentication
- Authorization
- Audit
- Configuration / Secrets
- Storage contracts
- Rate limiting
- Telemetry contracts

## Product Integration

Athkachatbots consumes reusable platform capabilities for:

- Knowledge
- Agent execution
- Evaluation
- Identity and tenant isolation

Athkachatbots keeps product-specific concerns such as:

- SaaS onboarding
- Customer portal
- Widget experience
- Product-specific settings

## Migration Strategy

The current codebase will not be rewritten.

Migration order:

1. Document ownership.
2. Stabilize contracts.
3. Add tests around boundaries.
4. Refactor dependencies gradually.
5. Move files only when useful.
6. Preserve working functionality during migration.
