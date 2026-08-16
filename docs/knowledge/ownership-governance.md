# Knowledge Ownership Governance

## Principle: One Fact — One Owner

The organization that creates or is accountable for a fact remains its
business and functional owner. TX AI Lab operates processing and platform
controls. Athkachatbots is Product #1 and receives permission to use approved
knowledge; product use does not transfer ownership.

## Roles

- **Business owner:** accountable for correctness, purpose, and permitted use.
- **Data steward/reviewer:** validates metadata, quality, classification, and
  lifecycle transitions when appointed.
- **Tenant:** security and contractual boundary for customer-owned knowledge.
- **TX AI Lab Knowledge Platform:** processes, stores, indexes, retrieves, and
  enforces approved platform controls.
- **Product:** consumes permitted knowledge through platform contracts.
- **Operations/Security:** protects storage, backups, secrets, and access.

Named people and organizational approvers are TBD.

## Currently Implemented

- Tenant and agent ownership scopes.
- Knowledge-base assignment.
- Source/file metadata and content hashes.
- Processing status and timestamps.
- Tenant-scoped repositories, retrieval, jobs, mutations, and audit foundations.

The current `tenant_id` identifies the security owner boundary but does not by
itself implement the complete business-owner/steward governance model.

## Target / Not Yet Implemented

- Explicit business owner and sector.
- Product-use permissions independent of tenant assignment.
- Created-by and updated-by governance actors for all lifecycle changes.
- Reviewer/approver identity and approval evidence.
- Version lineage and active-version attribution.
- Retention, effective date, expiry, legal hold, and archive policy.
- Cross-product shared-knowledge permissions.

## Required Metadata

| Field | Purpose | Current status |
|---|---|---|
| owner | Business/functional accountability | Target |
| sector | Domain and policy context | Target |
| tenant | Security/customer scope | Implemented in core records |
| source | Provenance and display | Partially implemented |
| classification | Security/provider policy | Target |
| version | Lineage and reproducibility | Technical replacement only |
| approval_status | Governance lifecycle | Target |
| created_by | Attribution | Partial via selected audit flows |
| updated_by | Attribution | Partial via selected audit flows |
| retention_policy | Required preservation/deletion | Target |
| effective_date | When facts apply | Target |
| expiry_date | When facts must stop applying | Target |

## Product Permission Rule

A product may retrieve knowledge only when tenant, product, agent assignment,
lifecycle state, classification, and purpose permit it. The pilot currently
enforces tenant/agent/knowledge-base assignment; product identity and the full
governance policy remain target capabilities.

## Training Use

Customer knowledge and conversations must never become training data by
default. Any evaluation or fine-tuning dataset requires explicit ownership,
classification, purpose, approval, versioning, and retention decisions.

## Deletion Accountability

The owner authorizes deletion subject to contractual/legal requirements. TX AI
Lab must execute and evidence deletion from active stores and manage backup
expiry. Product teams must not maintain undocumented copies.
