# TX AI Lab - Scope and Assumptions

## Current Scope

This architecture covers the Controlled Pilot phase of TX AI Lab.

In scope:

- Modular Monolith architecture
- Multi-tenant platform
- Athkachatbots as Product #1
- Knowledge Platform foundation
- Agent Runtime foundation
- Evaluation foundation
- Shared authentication and tenancy
- Provider abstractions
- Pilot-level backup, logs, health checks, and telemetry
- End-to-end Athkachatbots integration

## Out of Scope for This Phase

The following are intentionally deferred:

- Microservices
- Kubernetes
- Billing platform
- Model training or fine-tuning
- Advanced multi-provider routing
- Complex workflow engine
- Full enterprise data governance
- Multi-region deployment
- Full production SLO implementation
- Dedicated vector database migration

## Assumptions

- PostgreSQL + pgvector remains the primary database and vector store.
- DeepSeek is the current generation provider.
- Voyage is the current embedding and reranking provider.
- Provider implementations must remain replaceable through contracts.
- Tenant isolation is mandatory.
- Existing working functionality must be preserved during refactoring.
- Architecture changes must be incremental and test-protected.

## Pilot Principle

The goal of the pilot is not maximum scale.

The goal is to validate:

- correctness
- quality
- tenant isolation
- latency
- reliability
- cost
- operational behavior

before Production Readiness.
