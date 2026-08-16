# ADR-008: Controlled Pilot Hosting

- **Status:** Proposed
- **Owner:** Operations
- **Approver:** TBD
- **Date:** 2026-08-16

## Context / Problem

The Controlled Pilot needs a stable, affordable deployment that can validate
functionality and measurements. The current Compose topology runs PostgreSQL,
Redis, API, migrations, local upload storage, and an ingestion worker and may
be hosted on a single server.

## Options Considered

1. A hardened single-server deployment for the limited pilot.
2. Multi-host production topology before pilot measurement.
3. Kubernetes.
4. Managed platform services for every component immediately.

## Decision

A single-server Docker Compose topology may be accepted for the Controlled
Pilot after TLS, backup, logging, health, secret, and restore assumptions are
reviewed. It is not automatically an approved production architecture.
Kubernetes and premature service decomposition are out of scope.

## Rationale

This minimizes cost and operational complexity while the team measures
quality, capacity, reliability, and support burden.

## Consequences / Cost

- The host is a major failure domain.
- Pilot capacity and recovery limits must be documented and monitored.
- Production approval requires a separate evidence-based topology decision.

## Risks

- Host loss can affect API, worker, database, Redis, and local uploads.
- Resource contention may distort latency or worker throughput.
- Pilot convenience could be mistaken for production readiness.

## Revisit Trigger

Revisit before production approval and earlier when measured capacity,
availability, security isolation, recovery, or customer requirements exceed
the documented pilot envelope.
