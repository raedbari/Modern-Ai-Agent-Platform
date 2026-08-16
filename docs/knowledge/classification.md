# Knowledge Classification

> **Workstream D — TX AI Lab Knowledge Platform**
> Authority: Classification levels are defined by the platform. Products display classification but do not define it.

---

## 1. Data Classification Levels

The platform supports three classification levels for KnowledgeBases and their documents.

| Level        | Code          | Description | Example content |
|--------------|---------------|-------------|-----------------|
| **Public**   | `public`      | Intended for unrestricted distribution. May be shared outside the organization without restriction. | Marketing material, public FAQs, published regulations |
| **Internal** | `internal`    | For use within the organization and its authorized product tenants. Default level for all new KBs. | Internal policies, operational guides, tenant-specific product knowledge |
| **Restricted** | `restricted` | Sensitive content with limited access. Requires explicit authorization per product/agent. Additional audit controls apply. | Legal documents, financial data, personally-identifiable information, regulated content |

### Default Classification
All new KnowledgeBases default to `internal` unless explicitly set at creation time. This is enforced at the database level:

```sql
classification VARCHAR(32) NOT NULL DEFAULT 'internal'
```

Products **must not** escalate a classification level (e.g. change `restricted` to `internal`) — only a platform admin may reduce classification.

---

## 2. Classification Enforcement Rules

### 2.1 Access Control by Classification

| Classification | Who can retrieve? | Who can manage? |
|----------------|-------------------|-----------------|
| `public`       | Any agent in the tenant | Tenant admin |
| `internal`     | Agents explicitly attached to the KB | Tenant admin |
| `restricted`   | Agents explicitly attached + approved | Platform admin + Tenant admin |

> Note: `restricted` enforcement beyond the `internal` level is a **design-later** item. The classification field is stored now; fine-grained ACL enforcement per classification level will be implemented in a future sprint.

### 2.2 Classification Inheritance

- A Document inherits the classification of its KnowledgeBase.
- A Document may not have a lower (less restrictive) classification than its parent KB.
- Cross-KB document movement is forbidden. A document always belongs to exactly one KB.

### 2.3 Classification Change Rules

| Change               | Allowed? | Who can perform? | Notes |
|----------------------|----------|------------------|-------|
| public → internal    | No       | —                | Escalation is irreversible without platform admin |
| internal → restricted| Yes      | Tenant admin     | Downgrades access for all attached agents |
| restricted → internal| Yes      | Platform admin only | Requires audit justification |
| internal → public    | No       | —                | Escalation is irreversible without platform admin |
| public → restricted  | Yes      | Platform admin only | Emergency restriction |

> Implemented now: field stored + default enforced.
> ACL enforcement on change: **design-later**.

---

## 3. Classification and the Three-Layer Ownership Model

```
Layer 1 — Source Organization
  └─ Sets initial classification level at knowledge contribution time
  └─ Classification cannot be reduced by Layer 2 or Layer 3 without Layer 1 consent

Layer 2 — TX AI Lab
  └─ Stores and enforces classification in the platform data model
  └─ May increase classification (restrict) on operational grounds
  └─ Owns the default classification policy (default = internal)

Layer 3 — Product (Athkachatbots)
  └─ Reads classification to determine what to display in the UI
  └─ May NOT change classification
  └─ May NOT serve restricted content without explicit platform authorization
```

---

## 4. Product Independence Rules

### What products may do
- Read the `classification` field from the KnowledgeBase API response.
- Display classification level to the user (e.g. a badge in the KB list view).
- Refuse to surface `restricted` KB content in public-facing chat interfaces (UI-level guard).

### What products must NOT do
- Store a copy of the classification level independently of the platform.
- Create KBs with `restricted` classification without platform admin approval.
- Use classification to bypass or modify tenant isolation.
- Override the platform's retrieval filter based on product-defined classification rules.

---

## 5. Retrieval Behavior by Classification

The `RetrievalService` enforces classification at query time:

```
Query arrives with (tenant_id, agent_id, query_text)
  │
  ├─ Identify KBs attached to agent
  │    └─ Filter: classification IN (public, internal, restricted_if_authorized)
  │
  ├─ Execute pgvector similarity search
  │    └─ WHERE tenant_id = :tenant_id
  │         AND knowledge_base_id IN (:authorized_kb_ids)
  │         AND document.status IN ('ready', 'active')
  │
  └─ Return ranked chunks
```

> The retrieval service never leaks chunks from a KB the requesting agent is not authorized for, regardless of classification level.

---

## 6. Tenant Isolation and Classification (Interaction)

Classification operates **within** a tenant's isolation boundary. It is never a substitute for tenant isolation.

| Scenario | Behavior |
|----------|----------|
| Tenant A queries Tenant B's `public` KB | Denied — tenant boundary takes precedence |
| Tenant A agent queries own `restricted` KB without authorization | Denied — classification ACL |
| Tenant A agent queries own `internal` KB it is attached to | Allowed |
| Tenant A agent queries own `restricted` KB with explicit authorization | Allowed (design-later: authorization model) |

Cross-tenant access is always denied regardless of classification level. There is no "public" classification that enables cross-tenant access.

---

## 7. Object Storage Boundary and Classification

| Storage layer | Holds | Classification applied? |
|---------------|-------|-------------------------|
| PostgreSQL (metadata) | KB record with `classification` field | Yes — field present |
| PostgreSQL (chunks + vectors) | Chunk text, embeddings | Inherited from parent document/KB |
| Object Storage (future) | Original files, derived files | Must replicate classification tag as object metadata at upload time |

When object storage is introduced (see `ownership-governance.md`), the `classification` value must be stored as object metadata to enable bucket-level or prefix-level access policies.

---

## 8. Sprint Implementation Summary

| Item | Status |
|------|--------|
| `classification` field on `KnowledgeBase` model | **add-now** |
| Default value `internal` enforced at DB level | **add-now** |
| Classification read in API responses | **add-now** |
| Fine-grained ACL enforcement by classification level | design-later |
| Object storage classification tagging | design-later |
| Cross-classification escalation approval workflow | design-later |
| `restricted` authorization model for agents | design-later |
