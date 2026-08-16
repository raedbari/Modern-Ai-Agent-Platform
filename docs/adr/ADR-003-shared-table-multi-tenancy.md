# ADR-003: Shared-Table Multi-Tenancy

- **Status:** Proposed
- **Owner:** Shared Platform Services
- **Approver:** TBD
- **Date:** 2026-08-16

## Context / Problem

Athkachatbots must isolate multiple customers while keeping the pilot simple
to deploy and operate. The current database uses shared tables with `tenant_id`
and trusted authentication contexts.

## Options Considered

1. Shared database and shared tables with mandatory tenant filtering.
2. Schema per tenant.
3. Database per tenant.
4. A future hybrid based on classification or regulation.

## Decision

Use shared PostgreSQL tables with `tenant_id` for the Controlled Pilot.
Identity must resolve to a trusted tenant context before repository or service
access. Tenant identity supplied in untrusted request bodies is not authority.

## Rationale

This matches the implementation, minimizes pilot operations, and supports the
planned ten-customer scenario while preserving a path to stronger isolation
if evidence requires it.

## Consequences / Cost

- Every tenant-owned query and mutation must filter by trusted tenant context.
- Composite constraints, authorization tests, and auditability are required.
- A single schema is easier to migrate and back up.

## Risks

- A missed filter can cause cross-tenant disclosure or mutation.
- Administrative privileges have a larger blast radius.
- Noisy tenants can share database resources.

## Revisit Trigger

Revisit for regulated or highly sensitive customers, demonstrated noisy-neighbor
impact, contractual isolation needs, or an unacceptable residual leakage risk.
