# Knowledge Lifecycle

> **Workstream D — TX AI Lab Knowledge Platform**
> Authority: Platform team. Products must not define or override lifecycle rules.

---

## 1. Target Lifecycle State Machine

```
                         ┌─────────┐
                         │  DRAFT  │  (document uploaded, not yet validated)
                         └────┬────┘
                              │ submit for review
                              ▼
                         ┌─────────┐
                         │ REVIEW  │  (under content / compliance review)
                         └────┬────┘
                              │ approve
                              ▼
                         ┌──────────┐
                         │ APPROVED │  (approved, not yet ingested/published)
                         └────┬─────┘
                              │ publish (trigger ingestion)
                              ▼
                        ┌───────────┐
                        │ PUBLISHED │  (ingestion in-flight: parse→chunk→embed)
                        └─────┬─────┘
                              │ activate (ingestion complete, searchable)
                              ▼
                         ┌────────┐
                         │ ACTIVE │  ◄─── the only state that serves retrieval
                         └───┬────┘
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
       ┌────────────┐  ┌──────────┐  ┌─────────┐
       │ SUPERSEDED │  │ ARCHIVED │  │ DELETED │
       └────────────┘  └──────────┘  └─────────┘
         replaced by     soft-delete   hard-delete
         newer version   (recoverable) (irrecoverable)
```

### Terminal States

| State      | Description                                                  | Recoverable? |
|------------|--------------------------------------------------------------|--------------|
| SUPERSEDED | Replaced by a newer version via atomic reindex               | No           |
| ARCHIVED   | Soft-deleted — metadata preserved, chunks not served         | Yes (re-activate) |
| DELETED    | Physical removal of metadata, chunks, embeddings             | No           |

---

## 2. Current → Target State Mapping

| Current State (`DocumentProcessingStatus`) | Target State | Sprint Action        | Notes |
|---------------------------------------------|--------------|----------------------|-------|
| `PENDING`                                   | `DRAFT`      | alias / rename       | upload received, not yet processed |
| `PROCESSING`                                | `PUBLISHED`  | document as in-flight | ingestion pipeline is running |
| `READY`                                     | `ACTIVE`     | alias — add-now      | chunks indexed, retrieval enabled |
| `FAILED`                                    | `FAILED`     | keep unchanged       | terminal error state, no retrieval |
| _(not present)_                             | `SUPERSEDED` | **add-now**          | set when atomic reindex succeeds |
| _(not present)_                             | `ARCHIVED`   | **add-now**          | set on soft-delete or explicit archive |
| _(not present)_                             | `DRAFT`      | design-later         | separate pre-upload state |
| _(not present)_                             | `REVIEW`     | design-later         | approval workflow |
| _(not present)_                             | `APPROVED`   | design-later         | approval workflow |
| _(not present)_                             | `DELETED`    | design-later         | physical delete with full cleanup |

### Sprint Scope (add-now)
- Add `SUPERSEDED` and `ARCHIVED` to `DocumentProcessingStatus` enum.
- Treat `READY` as semantically equivalent to `ACTIVE` until enum rename is scheduled.
- FAILED remains a terminal error state with no automatic recovery.

---

## 3. KnowledgeBase Lifecycle

```
  ┌────────┐                ┌──────────┐
  │ ACTIVE │ ◄──────────── │ INACTIVE │
  └───┬────┘  re-activate   └──────────┘
      │
      │ archive
      ▼
  ┌──────────┐
  │ ARCHIVED │  (no new documents, no retrieval)
  └──────────┘
```

| State    | Documents accepted? | Retrieval served? | Sprint scope |
|----------|--------------------|-------------------|--------------|
| ACTIVE   | Yes                | Yes               | existing     |
| INACTIVE | No                 | No                | existing     |
| ARCHIVED | No                 | No                | add-now (doc only) |

---

## 4. Valid Transitions

### Document transitions (enforced by platform services)

| From       | To          | Trigger                          |
|------------|-------------|----------------------------------|
| PENDING    | PROCESSING  | ingestion job starts             |
| PROCESSING | READY       | all chunks embedded & persisted  |
| PROCESSING | FAILED      | any pipeline stage error         |
| READY      | SUPERSEDED  | atomic reindex succeeds          |
| READY      | ARCHIVED    | tenant or admin archives doc     |
| FAILED     | PENDING     | tenant triggers retry            |
| ARCHIVED   | READY       | tenant restores doc (design-later) |

### Forbidden transitions (platform must reject)
- Any state → READY/ACTIVE by product-level code (only platform services may set ACTIVE)
- SUPERSEDED → anything (terminal)
- DELETED → anything (terminal)

---

## 5. Migration Path for Deferred States

### DRAFT state
**Trigger**: pre-validation upload flow is introduced.
**Migration**: existing PENDING records without a validation timestamp stay PENDING; new uploads enter DRAFT.
**Estimated sprint**: post-Pilot Phase 2.

### REVIEW / APPROVED workflow
**Trigger**: compliance team requires content approval before knowledge is published.
**Migration**: platform adds `approval_status` field to Document (already classified as `design-later`). Existing records get `approval_status = auto-approved` retroactively.
**Estimated sprint**: post-Pilot Phase 2.

### DELETED (physical)
**Trigger**: regulatory retention window expires or explicit admin purge.
**Migration**: soft-delete (ARCHIVED) is the current mechanism. Physical deletion requires a scheduled cleanup job that respects `retention_policy` (design-later field).
**Estimated sprint**: post-Pilot, when retention_policy is implemented.

---

## 6. Retrieval Eligibility

Only documents in `READY` / `ACTIVE` state are eligible to serve retrieval requests. The platform's retrieval service (`RetrievalService`) must filter chunks by document status at query time:

```sql
-- Only ACTIVE/READY chunks served
WHERE d.tenant_id = :tenant_id
  AND d.knowledge_base_id = :kb_id
  AND d.status IN ('ready', 'active')
```

---

## 7. Audit Events

| Transition              | Audit event emitted? | Notes |
|-------------------------|----------------------|-------|
| PENDING → PROCESSING    | Yes (via IngestionJob) | job_started |
| PROCESSING → READY      | Yes                  | ingestion_complete |
| PROCESSING → FAILED     | Yes                  | ingestion_failed |
| READY → SUPERSEDED      | Yes                  | document_superseded |
| READY → ARCHIVED        | Yes                  | document_archived |
| FAILED → PENDING        | Yes                  | ingestion_retry |

Full audit log infrastructure is owned by the platform. Products must not suppress or bypass audit events.
