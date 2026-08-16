# Knowledge Ownership & Governance

> **Workstream D — TX AI Lab Knowledge Platform**
> Authority: Platform team. This model is enforced by platform services, not by product UIs.

---

## 1. Three-Layer Ownership Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LAYER 1 — Source Organization                     │
│                        (Business Owner)                             │
│                                                                     │
│  • Owns the original content and has ultimate approval authority    │
│  • Defines retention requirements and classification level          │
│  • Represented by: owner field (admin/org identifier)               │
│  • Example: a government ministry, a corporate HR department        │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ delegates ingestion & management
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LAYER 2 — TX AI Lab                            │
│                    (Platform / Process Operator)                    │
│                                                                     │
│  • Owns the platform infrastructure and data pipeline               │
│  • Enforces lifecycle rules, chunking strategy, embedding config    │
│  • Holds tenant isolation guarantees                                │
│  • Represented by: tenant_id + platform service accounts            │
│  • No product may override TX AI Lab's lifecycle or isolation rules │
└─────────────────────────────┬───────────────────────────────────────┘
                              │ grants permission-to-use
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   LAYER 3 — Product (Athkachatbots)                  │
│                       (Permission Holder)                           │
│                                                                     │
│  • Receives read access to a KnowledgeBase via agent association    │
│  • May display knowledge status in product UI                       │
│  • May NOT define chunking rules, version activation, or embedding  │
│  • May NOT grant itself access to other tenants' knowledge          │
│  • Represented by: agent_id association on Document                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Ownership Invariants
1. A KnowledgeBase belongs to exactly one tenant (Layer 2 scope). It is never "owned" by a product.
2. Products attach agents to knowledge bases — they do not own the knowledge base.
3. The Source Organization's classification decision (Layer 1) overrides any product-level classification.
4. TX AI Lab (Layer 2) is the sole authority for lifecycle transitions, embedding parameters, and tenant isolation.

---

## 2. Governance Metadata Field Classification

### 2.1 KnowledgeBase Fields

| Field               | Category    | Action       | Rationale |
|---------------------|-------------|--------------|-----------|
| `id`                | existing    | keep         | PK, no change |
| `tenant_id`         | existing    | keep         | primary isolation key |
| `name`              | existing    | keep         | human label |
| `description`       | existing    | keep         | human notes |
| `status`            | existing    | keep         | ACTIVE/INACTIVE |
| `owner`             | add-now     | add `created_by_admin_id` FK | maps to Layer 1 business owner identity |
| `classification`    | add-now     | add `classification` VARCHAR(32) DEFAULT 'internal' | drives access control and display rules |
| `sector`            | design-later | document only | industry/vertical (e.g. finance, health) |
| `retention_policy`  | design-later | document only | ISO 8601 duration string (e.g. P7Y) |
| `effective_date`    | design-later | document only | when KB knowledge becomes valid |
| `expiry_date`       | design-later | document only | when KB knowledge expires |

### 2.2 Document Fields

| Field               | Category    | Action       | Rationale |
|---------------------|-------------|--------------|-----------|
| `id`                | existing    | keep         | PK |
| `tenant_id`         | existing    | keep         | primary isolation key |
| `knowledge_base_id` | existing    | keep         | parent KB |
| `agent_id`          | existing    | keep         | optional product context |
| `source_name`       | existing    | keep         | maps to `source` in target model |
| `original_filename` | existing    | keep         | file identity |
| `mime_type`         | existing    | keep         | pipeline routing |
| `file_size_bytes`   | existing    | keep         | operational |
| `content_hash`      | existing    | keep         | deduplication + version identity |
| `status`            | existing    | keep         | lifecycle state (extended add-now) |
| `failure_reason`    | existing    | keep         | safe error message |
| `created_at`        | existing    | keep         | audit timestamp |
| `updated_at`        | existing    | keep         | audit timestamp |
| `version_number`    | add-now     | add INTEGER DEFAULT 1 | maps to `version` in target model |
| `superseded_by_id`  | add-now     | add FK → documents.id (nullable) | replacement chain for atomic reindex |
| `created_by`        | add-now     | add VARCHAR(255) nullable | maps to `created_by` in target model |
| `approval_status`   | design-later | document only | DRAFT/PENDING_REVIEW/APPROVED workflow |
| `sector`            | design-later | document only | inherited from KB or set per-document |
| `effective_date`    | design-later | document only | when document knowledge becomes valid |
| `expiry_date`       | design-later | document only | when document knowledge expires |

### 2.3 Target Model → Current Model Mapping

This table cross-references the target governance model from the sprint specification:

| Target Field      | Maps To                    | Category     | Notes |
|-------------------|----------------------------|--------------|-------|
| `owner`           | `KnowledgeBase.created_by_admin_id` | add-now | Layer 1 identity |
| `sector`          | _(not mapped yet)_         | design-later | KB + Document attribute |
| `tenant`          | `Document.tenant_id` / `KnowledgeBase.tenant_id` | existing | core isolation key |
| `source`          | `Document.source_name`     | existing     | logical source label |
| `classification`  | `KnowledgeBase.classification` | add-now  | public / internal / restricted |
| `version`         | `Document.version_number`  | add-now      | integer, starts at 1 |
| `approval_status` | _(not mapped yet)_         | design-later | approval workflow |
| `created_by`      | `Document.created_by`      | add-now      | admin/user who uploaded |
| `updated_by`      | _(not mapped yet)_         | design-later | last modifier identity |
| `retention_policy`| _(not mapped yet)_         | design-later | ISO 8601 duration |
| `effective_date`  | _(not mapped yet)_         | design-later | validity start |
| `expiry_date`     | _(not mapped yet)_         | design-later | validity end |

---

## 3. Deferred Governance Fields (design-later)

The following fields are documented here but **not implemented in this sprint**. They must not be added to models or APIs until a dedicated sprint designs their semantics and migration.

### sector
- Purpose: categorize knowledge by industry vertical (finance, government, health, retail, …).
- Design consideration: should be a controlled vocabulary, likely a separate lookup table.
- Dependency: classification taxonomy must be agreed across source organizations.

### retention_policy
- Purpose: define how long knowledge must be kept and when it may be purged.
- Design consideration: ISO 8601 duration string (e.g. `P7Y` = 7 years). Requires a scheduled cleanup job.
- Dependency: physical deletion lifecycle state (DELETED) must be implemented first.

### approval_status
- Purpose: track content approval workflow (DRAFT → PENDING_REVIEW → APPROVED → REJECTED).
- Design consideration: separate `approval_status` field on Document, with audit trail per transition.
- Dependency: REVIEW/APPROVED lifecycle states (design-later in lifecycle.md).

### effective_date / expiry_date
- Purpose: time-bound knowledge validity (e.g. a regulation that takes effect on 2025-01-01 and expires on 2026-12-31).
- Design consideration: retrieval service must filter out expired knowledge at query time.
- Dependency: retention_policy and approval_status should be in place first.

### updated_by
- Purpose: track the identity of the last person who modified a document or KB.
- Design consideration: requires an update audit log, not just a timestamp.
- Dependency: admin identity model must be stable.

---

## 4. Product Independence Rules

Products (e.g. Athkachatbots) interact with the Knowledge Platform through the published API surface only:

| Allowed for products                              | Forbidden for products |
|---------------------------------------------------|------------------------|
| Create / list / delete KnowledgeBases (own tenant) | Define chunking strategy |
| Upload documents to a KB                          | Set version activation rules |
| Check document / KB status                        | Override tenant isolation |
| Attach a KB to an agent                           | Call embedding APIs directly |
| Display knowledge status in UI                    | Modify lifecycle state directly |
| Query retrieval endpoint                          | Grant cross-tenant KB access |

Any business logic that would need to change if the product UI changed must live in platform services, not in the product.

---

## 5. Governance Enforcement Points

| Rule | Enforcement Location |
|------|----------------------|
| Tenant isolation | All repository methods (mandatory `tenant_id` parameter) |
| Version uniqueness | Partial unique index: one ACTIVE doc per (tenant_id, kb_id, original_filename) |
| Atomic reindex | Single DB transaction in `activate_prepared_reindex` |
| Classification default | DB DEFAULT 'internal' on `knowledge_bases.classification` |
| Lifecycle transitions | `IngestionService` and `KnowledgeService` — never product route handlers |
| Embedding input_type | `EmbeddingService` — `input_type="document"` for chunks, `input_type="query"` for search |
