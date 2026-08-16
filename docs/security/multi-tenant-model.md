# Multi-Tenant Security Model

## Status and Scope

This document defines the proposed Architecture v1.0 tenant model for the
Controlled Pilot. The current model is a shared PostgreSQL database with
shared tables and mandatory `tenant_id` scoping. It does not approve the
system for production.

## Request Trust Chain

```text
Authenticated identity or issued credential
  -> server-side tenant resolution
  -> trusted tenant and role context
  -> authorization policy
  -> tenant-scoped repository/service query
  -> tenant-scoped result and audit data
```

Tenant or agent identifiers supplied in a request body are not authority. An
agent selector, resource ID, or conversation ID must be resolved against the
trusted tenant context before use.

## Trust Boundaries

### Platform administrator

Admin sessions and legacy internal admin credentials operate in the platform
administrative boundary. Admin permissions are explicit and audited. Admin
access is not equivalent to a customer tenant session, and its larger blast
radius requires stronger operational control.

### Tenant user

A customer access token identifies a user and session. Effective tenant access
is derived from current, active database membership and active tenant state.
Roles constrain agent, knowledge, conversation, and Widget operations. Token
claims alone do not override current database state.

### Tenant API key

API keys are server-side tenant credentials. The stored record resolves the
tenant; the presented agent must belong to that tenant. Raw secrets are not
stored. API keys must not be embedded in public Widget code.

### Widget session

A Widget first presents a public Widget ID from an allowed Origin. Bootstrap
issues a short-lived token bound to tenant, agent, public Widget, session, and
normalized Origin. Chat rechecks the Origin, current allowed-origin record,
tenant/agent/Widget state, and session binding. A Widget token grants only the
public chat capability and is not a tenant-user or admin credential.

## Cross-Tenant Isolation Invariant

No read, write, retrieval candidate, rerank input, generated source, Widget
session, conversation, message, job, audit target, or stored object may cross
from one tenant context to another. Enforcement is layered:

- authentication resolves the trusted tenant;
- authorization checks role and resource ownership;
- repositories and services filter by `tenant_id` and, where applicable,
  `agent_id` and knowledge-base assignment;
- database constraints protect important composite relationships;
- retrieval filters before any candidate text is sent to Voyage reranking;
- tests cover cross-tenant repositories, APIs, RAG, Widget claims, and the
  complete Athkachatbots journey.

## Current Shared-Table Model

The Controlled Pilot uses one PostgreSQL database and shared tables. Tenant
ownership is represented by `tenant_id`. This is an accepted pilot decision
only after management and security review of ADR-003. It requires mandatory
filtering, least privilege, audit, tested migrations, backup protection, and
ongoing regression tests.

## Administrative and Operational Access

Database, backup, host, and secret access can bypass application isolation and
must be restricted to approved operators. Administrative actions should be
attributable and logged. The final operator roster, access-review interval,
and break-glass process are unresolved management/security decisions.

## Future Isolation Options

No stronger topology is committed now. Evidence may later justify:

- schema per tenant;
- database per tenant;
- isolated deployments for regulated or sensitive customers;
- a hybrid model with standard tenants on shared tables.

Triggers include regulation, contract requirements, classification, measured
noisy-neighbor effects, recovery needs, or unacceptable residual risk. Any
change requires an ADR and migration/isolation testing.
