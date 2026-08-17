# ADR-004: Separate Object Storage from Relational Metadata

- **Status:** Proposed
- **Owner:** Knowledge Platform / Operations
- **Approver:** TBD
- **Date:** 2026-08-16

## Context / Problem

Knowledge metadata, permissions, versions, chunks, and vector metadata belong
in PostgreSQL, while original and derived files need durable object storage.
The current pilot stores opaque file objects on a local filesystem volume.

## Options Considered

1. Local filesystem volume for the Controlled Pilot.
2. Managed S3-compatible object storage.
3. Store original file bytes in PostgreSQL.
4. Build a custom distributed storage service.

## Decision

Maintain a logical separation between PostgreSQL metadata and file objects.
Accept the existing local filesystem adapter only as a Controlled Pilot
implementation. Production requires an approved durable object-storage
implementation, backup policy, encryption, and deletion verification.

## Rationale

The separation already exists conceptually through opaque storage keys. It
avoids database bloat and permits a later storage-adapter replacement without
rewriting knowledge lifecycle logic.

## Consequences / Cost

- Pilot files and PostgreSQL must be backed up consistently.
- File deletion must accompany metadata, chunk, embedding, and index deletion.
- Production object storage adds service, retention, encryption, and network
  costs.

## Risks

- A single-host local volume can be lost with the host.
- Database/file backup inconsistency can create missing or orphaned objects.
- Incomplete deletion can violate customer and retention obligations.

## Revisit Trigger

Replace the local adapter before production approval, or earlier if pilot
durability, scale, remote-worker, security, or off-site backup needs demand it.
