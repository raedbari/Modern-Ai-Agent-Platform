# Sprint 1 — Knowledge Platform Foundation & Governance

## Owner
Developer 2

## Branch
`feat/knowledge-foundation-completion`

## Baseline SHA
`a6550335c80be836dd95fac8b81eff783c6eae8e`

## Mission
Evolve the current Athkachatbots knowledge subsystem into the first reusable **TX AI Lab Knowledge Platform** foundation without rewriting the application.

The Knowledge Platform must own data lifecycle, provenance, governance, ingestion, versioning, indexing, and tenant isolation independently of any single product UI.

---

## 1. Knowledge Platform Boundary

Document and enforce the reusable platform boundary:

```text
Data Source
→ Validation
→ Extraction
→ Cleaning
→ Metadata
→ Chunking
→ Embedding
→ Indexing
→ Retrieval
→ Update / Delete / Archive
```

Athkachatbots may call this capability, but product-specific code must not become the owner of knowledge lifecycle rules.

---

## 2. Knowledge Governance Metadata Foundation

Audit current models and introduce the minimum safe foundation for reusable knowledge governance.

Target metadata model includes:

```text
owner
sector
tenant
source
classification
version
approval_status
created_by
updated_by
retention_policy
effective_date
expiry_date
```

### Sprint Rule
Do not blindly add every field if current data model cannot support it safely.

Instead:
1. classify each field as `existing`, `add-now`, or `design-later`;
2. implement fields required for Pilot correctness/reuse;
3. document deferred fields.

Create:

```text
docs/knowledge/
├── lifecycle.md
├── ownership-governance.md
└── classification.md
```

---

## 3. Knowledge Ownership Model

Implement/document:

```text
Source Organization
→ remains business owner
TX AI Lab
→ platform/process operator
Product
→ receives permission to use knowledge
```

No product should implicitly own knowledge merely because it references a Knowledge Base.

Where code currently conflates tenant/product ownership, document and correct the minimum necessary boundary.

---

## 4. Knowledge Lifecycle

Management target:

```text
DRAFT
→ REVIEW
→ APPROVED
→ PUBLISHED
→ ACTIVE
→ SUPERSEDED / ARCHIVED / DELETED
```

### Sprint Requirement
Do not force a full enterprise workflow if current Pilot models do not support it.

Instead:
- map current states to target lifecycle;
- identify missing states;
- implement minimum states required for safe versioning/activation;
- document migration path.

---

## 5. Full Ingestion Lifecycle

Validate:

```text
Create KB
→ Upload Document
→ Ingestion Job
→ Validate
→ Parse
→ Clean
→ Chunk
→ Voyage document embedding
→ pgvector
→ Activate
```

Voyage document embedding must use:

```text
input_type="document"
```

---

## 6. Atomic Document Replacement

Critical invariant:

```text
V1 ACTIVE
  ↓
Upload V2
  ↓
PROCESSING
  ↓
Validate / Chunk / Embed
  ├─ Success → atomic switch → V2 ACTIVE, V1 SUPERSEDED
  └─ Fail    → V1 remains ACTIVE
```

Forbidden:

```text
old active chunks + new active chunks mixed
```

### Required Tests
- successful replacement
- failed replacement
- retry replacement
- old version remains usable after failure
- exactly one active version after success
- no mixed active chunks

---

## 7. Delete / Archive Correctness

When knowledge is deleted, determine and test removal/retirement across:

```text
Metadata
Documents
Object Storage references
Chunks
Embeddings
Indexes
Operational copies
Caches where applicable
```

Do not claim physical deletion where current storage architecture only supports logical deletion. Document exact semantics.

Audit events should be emitted where current audit infrastructure supports them.

---

## 8. Tenant Isolation

Tenant A must never be able to:

```text
list Tenant B KBs
read Tenant B documents
read Tenant B jobs
retrieve Tenant B chunks
replace Tenant B documents
reindex Tenant B documents
delete Tenant B documents
activate Tenant B knowledge
```

Tenant isolation is a release blocker.

---

## 9. Object Storage Boundary

Management target separates:

```text
PostgreSQL
→ metadata / ownership / permissions / versions / chunks / vector metadata

Object Storage
→ original files / derived files / exported datasets / backups
```

### Sprint Requirement
Do not introduce a new storage platform unless required.

Instead:
- document current file storage behavior;
- identify where original files live;
- define an ObjectStoragePort/interface if useful and not already present;
- document migration path to proper object storage.

---

## 10. Product Independence

Review APIs/services to ensure reusable knowledge logic does not depend on Athkachatbots-specific UI concepts.

A Product may:
- create/use KBs,
- attach them to agents,
- display knowledge status.

A Product must not define:
- chunking rules,
- version activation rules,
- tenant isolation rules,
- embedding implementation.

---

## Files / Areas to Inspect

```text
backend/app/services/knowledge/
backend/app/infrastructure/storage/
backend/app/infrastructure/database/
backend/app/api/routes/knowledge.py
backend/app/api/routes/admin_knowledge.py
backend/app/db/models.py
backend/app/domain/
backend/app/ai/providers/voyage.py
backend/app/workers/ingestion_worker.py
backend/alembic/versions/
backend/tests/test_ingestion_service.py
backend/tests/test_ingestion_jobs.py
backend/tests/test_postgres_knowledge_activation.py
backend/tests/test_knowledge_auth_boundary.py
backend/tests/test_tenant_scoped_document_repository.py
backend/tests/test_voyage_provider.py
frontend/src/components/knowledge/
docs/knowledge/
```

---

## Cross-Team Boundary With Developer 3

Developer 2 owns:

```text
source/document
→ version/governance
→ chunks
→ document embeddings
→ pgvector persistence
```

Developer 3 owns:

```text
query
→ retrieval orchestration
→ rerank
→ generation
→ evaluation
```

Shared contracts:
- retrieval result type
- source metadata
- knowledge version identifier
- tenant/product scope
- embedding configuration

Any breaking contract change requires coordination.

---

## Forbidden Changes

Do NOT:
- redesign Agent Runtime
- redesign DeepSeek integration
- create a second Voyage client
- add a new vector DB without benchmark/ADR
- rewrite all models/folders to target architecture
- add microservices
- add Kubernetes
- add Billing
- make product-specific UI logic the owner of knowledge rules

---

## Required Tests

```text
[ ] KB CRUD semantics
[ ] document upload
[ ] ingestion state transitions
[ ] validation/parse/chunk
[ ] Voyage document embedding
[ ] pgvector persistence
[ ] activation
[ ] failed ingestion safety
[ ] retry
[ ] reindex
[ ] replacement success
[ ] replacement failure preserves V1
[ ] no mixed versions
[ ] delete/archive semantics
[ ] tenant read isolation
[ ] tenant mutation isolation
[ ] tenant retrieval isolation
[ ] migration correctness
[ ] governance metadata invariants
```

---

## Definition of Done

```text
[ ] Knowledge Platform boundary documented
[ ] ownership-governance documented
[ ] classification foundation documented
[ ] current vs target lifecycle mapped
[ ] minimum governance metadata implemented/documented
[ ] ingestion lifecycle proven
[ ] atomic replacement proven
[ ] failed replacement safe
[ ] delete/archive semantics explicit
[ ] tenant isolation proven
[ ] object-storage boundary documented
[ ] Athkachatbots-specific coupling reduced where necessary
[ ] relevant tests green
```

---

## PR Title
`feat(knowledge): establish governed TX AI Lab knowledge platform foundation`

## PR Must Include
- current vs target knowledge lifecycle
- governance metadata decisions
- ownership model
- migrations
- atomic replacement behavior
- delete/archive semantics
- tenant isolation proof
- tests
- deferred governance items
