# Sprint 1 — TX AI Lab Platform Foundation (Management-Aligned)

## Baseline
`a6550335c80be836dd95fac8b81eff783c6eae8e`

## Architecture Direction
The repository remains a **single Modular Monolith**. We are not creating microservices or separate repositories in this Sprint.

Athkachatbots is treated as **Product #1** on top of reusable platform capabilities:

```text
TX AI Lab Platform
├── Knowledge Platform
├── Agent Runtime Platform
├── Evaluation Platform
├── Shared Platform Services
└── Products
    └── Athkachatbots
```

## Sprint Goal
Deliver the first management-aligned platform foundation that proves:

- Product vs Platform boundaries are explicit.
- Knowledge lifecycle is reusable outside Athkachatbots.
- Agent runtime is provider-abstracted and product-independent.
- Evaluation has a first real data model and repeatable runner.
- Tenant isolation remains mandatory across all platform domains.
- Athkachatbots still works as the first product.
- The controlled pilot becomes measurable, not merely functional.

## Workstreams

### Platform Core — Raed
Branch: `feat/platform-e2e-foundation`

Owns:
- Product vs Platform boundaries
- Architecture v1 documentation
- Shared tenancy/auth/contracts
- Athkachatbots product integration
- SaaS onboarding state machine
- Full E2E customer journey
- Pilot acceptance criteria
- Cross-domain integration governance

### Knowledge & Data — Developer 2
Branch: `feat/knowledge-foundation-completion`

Owns:
- Knowledge lifecycle
- Knowledge ownership/governance metadata
- Versioning/approval/classification foundations
- Ingestion and atomic replacement
- Tenant-safe persistence and retrieval boundaries
- Knowledge platform contracts

### Agent Runtime & Evaluation — Developer 3
Branch: `feat/agent-runtime-evaluation-foundation`

Owns:
- Agent runtime abstraction
- Provider interfaces
- Prompt versioning foundation
- Model/knowledge policy boundaries
- Grounded RAG runtime
- Evaluation data model
- Golden Questions
- Evaluation runner and baseline metrics

## Cross-Team Rules

1. No rewrite.
2. No microservices.
3. No Kubernetes.
4. No Billing.
5. No unrelated frontend redesign.
6. No provider-specific logic leaking across architectural boundaries.
7. Any cross-domain contract change requires owner review.
8. Tenant isolation is a release blocker.
9. Every workstream must leave tests and documentation behind.
10. New reusable logic belongs to Platform domains, not Athkachatbots product code.

## Sprint Exit Gate

Sprint 1 is complete when:

```text
Architecture v1 boundaries documented
AND
Knowledge platform foundation validated
AND
Agent runtime/provider boundaries validated
AND
Evaluation foundation runs
AND
Athkachatbots end-to-end journey passes
AND
Pilot acceptance criteria can be measured
```

This Sprint does not claim Production Readiness.
