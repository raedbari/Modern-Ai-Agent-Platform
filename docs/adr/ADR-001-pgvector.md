# ADR-001: PostgreSQL 16 and pgvector for the Controlled Pilot

- **Status:** Proposed
- **Owner:** Knowledge Platform
- **Approver:** TBD
- **Date:** 2026-08-16

## Context / Problem

The pilot needs transactional metadata, tenant-scoped knowledge, document
lifecycle state, and vector retrieval without introducing an additional data
platform. The repository already uses PostgreSQL 16 with pgvector and has
tested safe activation, replacement, deletion, and tenant-filtered retrieval.

## Options Considered

1. PostgreSQL 16 with pgvector.
2. A dedicated managed vector database.
3. Separate relational and self-hosted vector stores.

## Decision

Use PostgreSQL 16 and pgvector as the relational and vector architecture for
the Controlled Pilot. Keep vector access behind repository contracts. Do not
adopt a dedicated vector layer without measured need.

## Rationale

This preserves transactional lifecycle changes, reduces operating cost, and
matches the validated Modular Monolith. It is sufficient for pilot-scale
measurement and tenant-first filtering.

## Consequences / Cost

- One database must handle transactional and vector workloads.
- PostgreSQL backup and recovery cover both metadata and embeddings.
- Index tuning, storage growth, and query latency must be measured.
- The team avoids the cost and consistency work of a second datastore.

## Risks

- Vector workloads may contend with transactional traffic.
- Growth may expose indexing, storage, or latency limits.
- Incorrect queries could undermine tenant isolation; repository filtering
  and isolation tests remain mandatory.

## Revisit Trigger

Revisit when benchmarks show unacceptable retrieval latency, database
contention, storage growth, independent availability needs, or a justified
regulated-customer isolation requirement.
