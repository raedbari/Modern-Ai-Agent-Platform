# ADR-007: Knowledge Ownership Model

- **Status:** Proposed
- **Owner:** Knowledge Platform
- **Approver:** TBD
- **Date:** 2026-08-16

## Context / Problem

Knowledge used by Athkachatbots may originate from customers or other business
domains. Product use must not transfer business ownership to Athkachatbots or
to TX AI Lab.

## Options Considered

1. One Fact—One Owner, with products receiving permission to use knowledge.
2. Treat all uploaded data as Athkachatbots-owned.
3. Duplicate knowledge independently for each product without shared
   governance.

## Decision

The originating organization remains the business and functional owner. TX AI
Lab operates processing and platform controls. Athkachatbots and future
products receive explicit permission to use knowledge within tenant, product,
classification, and lifecycle policy.

## Rationale

Explicit ownership supports reuse, deletion, retention, audit, classification,
and future products without making a chatbot product the system of record.

## Consequences / Cost

- Target metadata includes owner, sector, tenant, source, classification,
  version, approval state, actors, retention, and effective/expiry dates.
- Permission and lifecycle governance must be implemented incrementally.
- Existing pilot metadata is incomplete and must not be described as the full
  target model.

## Risks

- Ambiguous owners can lead to unauthorized use or failed deletion.
- Shared knowledge may accidentally cross tenant or product boundaries.
- Governance overhead can exceed pilot needs if implemented prematurely.

## Revisit Trigger

Revisit when shared cross-product knowledge, sector-owned datasets, regulatory
obligations, or approved training datasets introduce new ownership roles.
