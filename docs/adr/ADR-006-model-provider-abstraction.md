# ADR-006: Model Provider Abstraction

- **Status:** Proposed
- **Owner:** Agent Runtime Platform
- **Approver:** TBD
- **Date:** 2026-08-16

## Context / Problem

Provider choice can change with quality, latency, cost, availability, and data
policy. Platform orchestration must not be owned by DeepSeek or Voyage APIs.

## Options Considered

1. Provider-independent generation, embedding, and reranking contracts.
2. Direct vendor SDK use throughout application services.
3. Build an advanced multi-provider router before pilot evidence.

## Decision

Provider contracts are the architecture; vendors are replaceable
implementations. Use DeepSeek for current generation and Voyage for current
embeddings and reranking. Keep provider-specific HTTP/SDK behavior in adapters.
Do not build advanced routing before a measured requirement exists. Ollama is
legacy only, not a target provider.

## Rationale

The contracts already support deterministic testing and isolate current
vendors. This enables future comparison or replacement without destabilizing
RAG, ingestion, or product code.

## Consequences / Cost

- Adapters must normalize results, errors, retries, tokens, and model identity.
- Contract evolution needs compatibility tests.
- A future router can be added behind the same application boundary.

## Risks

- Vendor features can leak into common contracts.
- Lowest-common-denominator interfaces can hide useful capabilities.
- Replaceability is unproven until another approved implementation is tested.

## Revisit Trigger

Revisit contracts when a second approved provider, failover policy, data
classification rule, or measured model-routing use case requires it.
