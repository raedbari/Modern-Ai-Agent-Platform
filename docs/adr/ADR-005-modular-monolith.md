# ADR-005: Modular Monolith in One Repository

- **Status:** Proposed
- **Owner:** Platform Architecture
- **Approver:** TBD
- **Date:** 2026-08-16

## Context / Problem

TX AI Lab must evolve reusable Knowledge, Agent Runtime, Evaluation, and
Shared Platform capabilities while Athkachatbots remains Product #1. The
current problem is ownership and boundaries, not deployment topology.

## Options Considered

1. One repository and Modular Monolith with logical domain boundaries.
2. Immediate microservice decomposition.
3. Rewrite into multiple repositories and deployments.

## Decision

Keep one repository, one backend application, and a Modular Monolith for the
Controlled Pilot. Define ownership and contracts first; refactor gradually
and move files only when useful. There will be no rewrite or premature
microservice split.

## Rationale

The current system already delivers working cross-domain flows. A Modular
Monolith preserves transactionality and delivery speed while allowing domain
boundaries to mature under tests.

## Consequences / Cost

- Domain boundaries require governance and automated checks rather than
  deployment isolation.
- One release can affect all modules.
- The team avoids distributed transactions, service discovery, and duplicated
  operations.

## Risks

- Technical-layer folders can obscure ownership.
- Unchecked imports can create coupling.
- Teams may mistake the target folder proposal for a mandatory reorganization.

## Revisit Trigger

Consider extraction only after measured independent scaling, deployment,
security isolation, reliability, performance, or team-ownership needs.
