# Knowledge Classification

## Status

This is a proposed Architecture v1.0 governance model. Classification fields,
automatic detection, redaction, provider routing, and enforcement are not yet
implemented. Pilot data must therefore be manually selected and reviewed under
an approved interim policy.

## Proposed Levels

| Level | Description | Default external-provider posture |
|---|---|---|
| Public | Approved for public disclosure | Allowed for approved purpose/provider |
| Internal | Non-public operational information | Owner and provider-policy approval required |
| Confidential | Customer, commercial, or sensitive information | Restricted; minimize/redact and use approved provider only |
| Restricted / regulated | Highly sensitive, legally controlled, or high-impact data | Block unless an explicitly approved controlled path exists |

Final names, definitions, examples, and owners require management and Security
approval. Unclassified data must not default to Public.

## Classification Decision Inputs

- business owner and tenant;
- sector and legal/regulatory obligations;
- personal, financial, health, credential, or security content;
- source and permitted purpose;
- provider contract, region, retention, and training-use terms;
- product audience and Widget/public exposure;
- retention, effective date, and expiry.

## Required Flow

```text
Source received
  -> identify owner and tenant
  -> validate source and file
  -> assign classification
  -> review permitted product and provider use
  -> approve/reject/quarantine
  -> publish and activate only if permitted
  -> reevaluate on version, owner, purpose, provider, or policy change
```

## Currently Implemented

- Tenant and agent scoping.
- File type/size checks and parsers for supported pilot formats.
- Source name, file metadata, hashes, statuses, jobs, and audit foundations.
- Tenant filtering before Voyage reranking.

These controls do not constitute classification or approval.

## Target Metadata

Classification is recorded with owner, sector, tenant, source, version,
approval status, actors, retention policy, effective date, and expiry date.
Changes must be auditable and tied to a knowledge version.

## Handling Rules

- **Public:** still requires integrity, provenance, and purpose checks.
- **Internal:** prevent accidental public Widget disclosure; provider use must
  be approved.
- **Confidential:** minimize content, redact where approved, restrict access,
  and apply stronger logging/retention controls.
- **Restricted:** block by default; an approved provider or local-provider path
  requires a separate security decision.

## Unresolved Decisions

- Final taxonomy and sector-specific overlays.
- Who assigns and approves classifications.
- Which pilot datasets are allowed with DeepSeek and Voyage.
- Redaction standards and verification.
- Malware/quarantine requirements.
- Reclassification and incident procedure.
