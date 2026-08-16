# Knowledge Lifecycle

## Purpose

Define the target TX AI Lab knowledge lifecycle while accurately recording the
smaller lifecycle implemented by the Controlled Pilot.

## Target Lifecycle — Not Yet Implemented

```text
DRAFT
  -> REVIEW
  -> APPROVED
  -> PUBLISHED
  -> ACTIVE
  -> SUPERSEDED / ARCHIVED / DELETED
```

- **DRAFT:** content has an owner but is not approved for use.
- **REVIEW:** designated reviewers validate accuracy, classification, source,
  and permitted use.
- **APPROVED:** governance approval is recorded.
- **PUBLISHED:** an approved version is prepared for product access.
- **ACTIVE:** retrieval may use the version under tenant/product permission.
- **SUPERSEDED:** a newer version replaced it; it remains retained only under
  policy.
- **ARCHIVED:** unavailable for normal retrieval but retained under policy.
- **DELETED:** removed from active systems and expired from backups according
  to the approved deletion and backup policy.

This state machine, its reviewers, and its approval records are target
governance. They are not present in the current database model.

## Currently Implemented

The pilot implements a technical document-processing lifecycle with pending,
processing, ready, and failed behavior. It supports parsing, chunking,
embedding, indexing, tenant/agent assignment, duplicate detection, durable
jobs, source metadata, replacement, activation, and deletion. Retrieval only
uses ready knowledge in the trusted tenant and agent scope.

The current implementation must not be described as business approval,
classification, retention, or complete version governance.

## Atomic Replacement

The required replacement invariant is implemented and must be preserved:

```text
V1 ACTIVE
  -> receive V2
  -> parse, chunk, embed, and validate V2
     -> success: atomically activate V2 and remove/supersede V1 chunks
     -> failure: keep V1 active and record V2 failure safely
```

No partially processed replacement may become retrieval evidence. Replacement
must remain tenant-scoped and auditable.

## Target Metadata — Not Yet Fully Implemented

- owner
- sector
- tenant
- source
- classification
- version
- approval_status
- created_by
- updated_by
- retention_policy
- effective_date
- expiry_date

Current records include tenant, agent, knowledge-base, source/file details,
processing status, timestamps, jobs, chunks, and audit foundations. The other
fields require approved models and incremental implementation.

## Deletion Target

An approved deletion must address metadata, original/derived files, chunks,
embeddings, indexes, caches or operational copies where applicable, and backup
expiry. Current knowledge deletion paths cover important active-system data,
but retention and backup-deletion evidence are unresolved.

## Required Decisions

- Who may submit, review, approve, publish, archive, and delete.
- Whether pilot customer uploads may become active immediately.
- Version identifier and active-version rules.
- Retention and legal-hold behavior.
- Classification and provider-use gates.
- Audit evidence required for each transition.
