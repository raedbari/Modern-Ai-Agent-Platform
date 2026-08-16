# TX AI Lab Architecture v1.0 Approval Checklist

## Review State

**READY FOR MANAGEMENT REVIEW**

This package is proposed. No checkbox below is evidence of approval until the
named authority records a decision. Architecture v1.0 is **not approved**.

- **Architecture Owner:** TBD
- **Management Approver:** TBD
- **Security Approver:** TBD
- **Operations Approver:** TBD
- **Review Date:** TBD
- **Decision Record / Minutes:** TBD

## Product vs Platform Boundaries

| Item | Reviewed | Approved |
|---|---|---|
| Athkachatbots is Product #1 over reusable platform domains | [ ] | [ ] |
| Knowledge, Agent Runtime, Evaluation, Shared Services ownership | [ ] | [ ] |
| Product-to-platform dependency direction | [ ] | [ ] |
| Incremental migration without rewrite | [ ] | [ ] |

## Architecture Decision Records

| Item | Reviewed | Approved |
|---|---|---|
| ADR-001 PostgreSQL 16 + pgvector | [ ] | [ ] |
| ADR-002 API-first AI providers | [ ] | [ ] |
| ADR-003 shared-table multi-tenancy | [ ] | [ ] |
| ADR-004 object-storage separation | [ ] | [ ] |
| ADR-005 Modular Monolith | [ ] | [ ] |
| ADR-006 model-provider abstraction | [ ] | [ ] |
| ADR-007 knowledge ownership | [ ] | [ ] |
| ADR-008 Controlled Pilot hosting | [ ] | [ ] |

## Multi-Tenancy

| Item | Reviewed | Approved |
|---|---|---|
| Identity-to-tenant trust chain | [ ] | [ ] |
| Cross-tenant isolation invariant | [ ] | [ ] |
| Admin, tenant-user, API-key, and Widget boundaries | [ ] | [ ] |
| Shared-table residual risk and revisit triggers | [ ] | [ ] |

## Security / Threat Model

| Item | Reviewed | Approved |
|---|---|---|
| Threat scope and security invariants | [ ] | [ ] |
| Existing controls are represented accurately | [ ] | [ ] |
| Current gaps and future mitigations | [ ] | [ ] |
| Risk owners and accepted residual risk | [ ] | [ ] |

## Provider Strategy

| Item | Reviewed | Approved |
|---|---|---|
| DeepSeek current generation use | [ ] | [ ] |
| Voyage current embedding/reranking use | [ ] | [ ] |
| Contracts are architecture; vendors are replaceable | [ ] | [ ] |
| Ollama recorded as legacy-only, not target architecture | [ ] | [ ] |
| Provider approval and outage assumptions | [ ] | [ ] |

## Data Classification

| Item | Reviewed | Approved |
|---|---|---|
| Proposed taxonomy and default handling | [ ] | [ ] |
| Unclassified data does not default to Public | [ ] | [ ] |
| External-provider decision flow | [ ] | [ ] |
| Interim manual pilot review and future enforcement | [ ] | [ ] |

## Knowledge Governance

| Item | Reviewed | Approved |
|---|---|---|
| One Fact—One Owner model | [ ] | [ ] |
| Target lifecycle and transition authorities | [ ] | [ ] |
| Target metadata and implementation gaps | [ ] | [ ] |
| Atomic replacement invariant | [ ] | [ ] |
| Deletion, retention, backup expiry, and training-use rules | [ ] | [ ] |

## Storage

| Item | Reviewed | Approved |
|---|---|---|
| PostgreSQL metadata vs file-object separation | [ ] | [ ] |
| Local filesystem explicitly limited to pilot | [ ] | [ ] |
| Production object-storage requirement and trigger | [ ] | [ ] |
| File/database reconciliation and deletion expectations | [ ] | [ ] |

## Capacity

| Item | Reviewed | Approved |
|---|---|---|
| Pilot 10 / Growth 100 / Scale 1,000 scenarios | [ ] | [ ] |
| Required workload and resource variables | [ ] | [ ] |
| No unverified benchmark claims | [ ] | [ ] |
| Evidence-based architecture exit points | [ ] | [ ] |

## Cost

| Item | Reviewed | Approved |
|---|---|---|
| TCO categories and allocation principles | [ ] | [ ] |
| Required price and usage inputs | [ ] | [ ] |
| Pilot unit-cost metrics | [ ] | [ ] |
| Budget/anomaly and AI cost/revenue decisions | [ ] | [ ] |

## Backup / DR

| Item | Reviewed | Approved |
|---|---|---|
| Pilot backup scope and off-site requirement | [ ] | [ ] |
| Proposed 24-hour RPO and 8-hour RTO | [ ] | [ ] |
| Restore-test acceptance criteria | [ ] | [ ] |
| Secret recovery and backup encryption | [ ] | [ ] |
| Production DR explicitly deferred to Phase 4 | [ ] | [ ] |

## Pilot Assumptions

| Item | Reviewed | Approved |
|---|---|---|
| Single-server hosting is pilot-only | [ ] | [ ] |
| No Kubernetes, premature microservices, or rewrite | [ ] | [ ] |
| Pilot measures quality, latency, cost, isolation, reliability, and operations | [ ] | [ ] |
| Production readiness is a separate phase and gate | [ ] | [ ] |

## Unresolved Risks and Decisions

| Item | Reviewed | Approved / Accepted |
|---|---|---|
| Named owners and approvers | [ ] | [ ] |
| Final classification taxonomy and pilot dataset eligibility | [ ] | [ ] |
| Provider contractual/data-handling approval | [ ] | [ ] |
| Backup technology, retention, encryption, and final RPO/RTO | [ ] | [ ] |
| Pilot capacity and acceptance thresholds | [ ] | [ ] |
| Cost inputs, currency, allocation, and budget thresholds | [ ] | [ ] |
| Operator access, incident ownership, and break-glass process | [ ] | [ ] |
| Malware scanning/quarantine threshold | [ ] | [ ] |

## Final Decision

- [ ] Architecture v1.0 approved.
- [ ] Architecture v1.0 approved with recorded conditions.
- [ ] Architecture v1.0 returned for revision.

**Decision:** TBD  
**Conditions / required follow-up:** TBD  
**Approver signatures or linked decision record:** TBD
