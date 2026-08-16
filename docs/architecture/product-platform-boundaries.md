# TX AI Lab - Product vs Platform Boundaries

## Purpose

Define clear ownership boundaries between reusable TX AI Lab platform capabilities and Athkachatbots product-specific capabilities.

## Knowledge Platform

Owns:

- Knowledge Bases
- Documents
- Document lifecycle
- Chunking
- Document embeddings
- Ingestion jobs
- Versioning
- Activation / replacement
- Delete / archive semantics
- Tenant-scoped vector storage
- Knowledge governance metadata

Does NOT own:

- Widget UI
- Customer onboarding
- Chatbot product settings
- Model generation logic

## Agent Runtime Platform

Owns:

- Agent execution
- Query embedding
- Retrieval orchestration
- Reranking
- Evidence selection
- Answerability policy
- Prompt execution
- Generation provider abstraction
- Grounded generation
- Citations
- Knowledge usage policy

Does NOT own:

- Document ingestion lifecycle
- SaaS onboarding
- Customer portal UI

## Evaluation Platform

Owns:

- Evaluation datasets
- Golden Questions
- Evaluation runs
- Retrieval metrics
- Groundedness metrics
- Refusal metrics
- Citation metrics
- Latency measurements
- Token and cost measurements
- Experiment comparisons

## Shared Platform Services

Owns:

- Tenancy
- Authentication
- Authorization / RBAC
- Audit
- Shared platform contracts
- Secrets/configuration
- Storage contracts
- Rate limiting
- Observability contracts

Shared services must not contain Athkachatbots-specific business logic.

## Athkachatbots Product

Owns:

- SaaS onboarding
- Customer application workflow
- Customer portal
- Chatbot creation experience
- Widget configuration
- Widget integration
- Product conversations experience
- Product-specific settings

Athkachatbots consumes Knowledge Platform, Agent Runtime, Evaluation, and Shared Platform capabilities.

## Dependency Direction

Preferred dependency direction:

Athkachatbots Product
    ↓
Platform Domains
    ↓
Shared Contracts / Infrastructure

Platform domains must not depend on Athkachatbots product-specific code.

## Migration Rule

This document defines ownership first.

It does NOT require moving all existing files immediately.

Existing code will be migrated gradually when contracts and tests are stable.
