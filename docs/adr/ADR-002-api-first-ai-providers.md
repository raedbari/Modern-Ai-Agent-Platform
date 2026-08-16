# ADR-002: API-First AI Providers

- **Status:** Proposed
- **Owner:** Agent Runtime Platform
- **Approver:** TBD
- **Date:** 2026-08-16

## Context / Problem

The pilot needs capable generation, embeddings, and reranking without buying
GPU infrastructure or operating model-serving clusters. Provider data use,
availability, latency, and cost must remain governed.

## Options Considered

1. External providers through authenticated APIs.
2. Self-host all models for the pilot.
3. A mixed model-serving platform before pilot measurement.

## Decision

Use API-first providers for the Controlled Pilot. DeepSeek is the current
generation implementation. Voyage is the current embedding and reranking
implementation. Provider calls must pass through platform contracts and data
policy checks. Ollama is legacy only and is not target architecture.

## Rationale

API-first delivery minimizes infrastructure investment, accelerates measured
validation, and lets the team compare quality, latency, and cost before making
hosting commitments.

## Consequences / Cost

- Provider usage and network traffic create variable operating cost.
- Secrets, timeouts, retries, and provider failure behavior require controls.
- Data sent externally must follow an approved classification policy.
- No GPU purchase or model-serving operations are required now.

## Risks

- Provider outage, policy change, latency, or price change.
- Sensitive data could be transmitted without adequate governance.
- Vendor-specific behavior could leak beyond provider adapters.

## Revisit Trigger

Revisit when provider reliability, cost, data classification, regulation, or
measured quality requires another approved provider or local deployment.
