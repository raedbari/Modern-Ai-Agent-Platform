# TX AI Lab — Architecture v1 Management Decisions

## Purpose

The technical Architecture v1.0 package is prepared and marked **READY FOR
MANAGEMENT REVIEW**. The items below are the remaining management decisions
needed to close Phase 1 — Architecture & Governance. Detailed rationale remains
in `docs/architecture/`, `docs/adr/`, and the governance documents; this file
records decisions only. Nothing below is approved until management marks it.

## MD-001 — Architecture Ownership and Approvers

- **Decision ID:** MD-001
- **Topic:** Name the Architecture Owner, Management Approver, Security
  Approver, and Operations Approver.
- **Why management needs to decide:** Architecture v1.0 cannot have accountable
  review, exceptions, or approval without named decision owners.
- **Current recommendation:** Assign one named person to each role; roles may be
  combined only when management explicitly accepts the reduced separation.
- **Alternatives:** Named individuals; named committees with a chair; temporary
  pilot approvers with a scheduled review date.
- **Impact of decision:** Establishes accountability for this gate and later
  architecture, security, and operational exceptions.
- **Recommended answer:** Record four named approvers before final approval.
- **Management decision:** [ ]
- **Owner / approver:** Architecture Owner: TBD; Management Approver: TBD;
  Security Approver: TBD; Operations Approver: TBD.

## MD-002 — Controlled Pilot Scope

- **Decision ID:** MD-002
- **Topic:** Approve 10 customers as the Controlled Pilot planning envelope.
- **Why management needs to decide:** Capacity, support, backup, cost, and
  acceptance planning need a bounded cohort.
- **Current recommendation:** Approve up to 10 controlled customers, admitted
  incrementally and subject to readiness checks.
- **Alternatives:** Smaller cohort; another explicitly bounded number; defer
  external customers until additional controls are complete.
- **Impact of decision:** Sets the Phase 2 planning envelope, not a capacity
  guarantee or commercial launch commitment.
- **Recommended answer:** Approve 10 as the planning maximum for the pilot.
- **Management decision:** [ ]
- **Owner / approver:** Product/Management Approver: TBD.

## MD-003 — Controlled Pilot Hosting

- **Decision ID:** MD-003
- **Topic:** Accept single-server Docker Compose hosting for the Controlled
  Pilot only.
- **Why management needs to decide:** The topology concentrates API, worker,
  database, Redis, and local-file failure risk on one host.
- **Current recommendation:** Accept it only within the bounded pilot after
  TLS, backup, restore, logging, health, secret, and support assumptions are
  accepted. This is explicitly not Production approval.
- **Alternatives:** Require selected managed/separate components before pilot;
  defer external pilot; approve another documented pilot topology.
- **Impact of decision:** Trades availability and recovery strength for lower
  pilot cost and operating complexity.
- **Recommended answer:** Approve for Controlled Pilot with recorded conditions;
  require a new Phase 4 production-topology decision.
- **Management decision:** [ ]
- **Owner / approver:** Operations Approver: TBD; Management Approver: TBD.

## MD-004 — Pilot Data Classification

- **Decision ID:** MD-004
- **Topic:** Approve the pilot taxonomy: Public, Internal, Confidential, and
  Restricted / Regulated.
- **Why management needs to decide:** Provider eligibility, Widget exposure,
  access, retention, and incident response depend on a common classification.
- **Current recommendation:** Approve the four levels and require unclassified
  data to be treated as non-public pending review.
- **Alternatives:** Adopt an existing corporate taxonomy; approve a smaller
  pilot taxonomy with a mapping to the corporate model.
- **Impact of decision:** Determines which pilot datasets can be admitted and
  what handling controls they require.
- **Recommended answer:** Approve the proposed taxonomy for pilot governance,
  subject to Security/data-owner review.
- **Management decision:** [ ]
- **Owner / approver:** Security Approver: TBD; Data Owners: TBD.

## MD-005 — Data Eligible for External AI Providers

- **Decision ID:** MD-005
- **Topic:** Decide what data may be sent to DeepSeek and Voyage.
- **Why management needs to decide:** Classification/redaction enforcement is
  not automated; external processing creates contractual and privacy exposure.
- **Current recommendation:** Permit Public data; permit Internal data only
  after owner and provider-policy approval; treat Confidential as blocked by
  default unless minimized/redacted and explicitly approved; block Restricted /
  Regulated data unless an approved alternative exists.
- **Alternatives:** Public-only external processing; broader approved provider
  matrix; approved redaction path; approved local/alternative provider.
- **Impact of decision:** Directly controls eligible pilot customers and data,
  provider risk, and required manual review.
- **Recommended answer:** Approve the conservative policy above and require a
  documented data-owner/Security decision for every non-Public pilot dataset.
- **Management decision:** [ ]
- **Owner / approver:** Security Approver: TBD; Data Owner: TBD; Management
  Approver: TBD.

## MD-006 — Provider Approval

- **Decision ID:** MD-006
- **Topic:** Approve DeepSeek for current generation and Voyage for current
  embeddings/reranking under the provider-data decision.
- **Why management needs to decide:** The providers process pilot content and
  create availability, contractual, cost, and data-handling dependencies.
- **Current recommendation:** Approve these implementations for eligible pilot
  data; keep generation, embedding, and rerank abstractions mandatory; record
  Ollama as legacy only and not target architecture.
- **Alternatives:** Approve a narrower data scope; select another reviewed
  provider; delay external provider use.
- **Impact of decision:** Enables the current RAG path without making either
  vendor permanent architecture.
- **Recommended answer:** Approve DeepSeek and Voyage for the Controlled Pilot,
  conditional on provider terms and MD-005.
- **Management decision:** [ ]
- **Owner / approver:** Management Approver: TBD; Security Approver: TBD;
  Provider Contract Owner: TBD.

## MD-007 — Knowledge Ownership

- **Decision ID:** MD-007
- **Topic:** Approve One Fact — One Owner.
- **Why management needs to decide:** Customer/sector knowledge needs clear
  authority for use, correction, retention, deletion, and future reuse.
- **Current recommendation:** The originating organization remains business and
  functional owner. TX AI Lab operates the platform; Athkachatbots receives
  permission to use knowledge and does not automatically own it.
- **Alternatives:** Product ownership of uploads; central AI Lab ownership;
  contract-specific ownership without a common principle.
- **Impact of decision:** Establishes accountability and prevents product use
  from silently transferring data ownership.
- **Recommended answer:** Approve One Fact — One Owner.
- **Management decision:** [ ]
- **Owner / approver:** Management Approver: TBD; Business/Data Owners: TBD.

## MD-008 — Knowledge Lifecycle Authorities

- **Decision ID:** MD-008
- **Topic:** Name who may REVIEW, APPROVE, PUBLISH, and ARCHIVE/DELETE knowledge.
- **Why management needs to decide:** The target lifecycle requires accountable
  business decisions beyond the currently implemented technical activation.
- **Current recommendation:** Data steward REVIEW; business/data owner APPROVE;
  authorized Knowledge Platform operator PUBLISH; owner plus authorized
  governance/operations role ARCHIVE or DELETE, subject to retention/legal hold.
- **Alternatives:** Customer self-approval for low-risk pilot data; centralized
  review board; sector-specific approvers.
- **Impact of decision:** Determines workflow, audit evidence, staffing, and how
  quickly pilot knowledge can become active.
- **Recommended answer:** Approve the role model above and name role holders or
  an interim pilot authority matrix.
- **Management decision:** [ ]
- **Owner / approver:** Knowledge Owner: TBD; Management Approver: TBD.

## MD-009 — Pilot Storage

- **Decision ID:** MD-009
- **Topic:** Accept current local filesystem upload storage for the Controlled
  Pilot and decide whether stronger object storage is required before external
  customers.
- **Why management needs to decide:** Local storage shares the host failure
  domain and is not production object storage.
- **Current recommendation:** Accept only if coordinated backup, encrypted
  off-site copy, restore test, deletion handling, and bounded pilot exposure are
  approved. Defer production object-storage selection to Phase 4.
- **Alternatives:** Require managed/S3-compatible object storage before external
  pilot; allow local storage only for internal testing; defer pilot.
- **Impact of decision:** Changes pilot durability, operating cost, schedule,
  and recovery risk.
- **Recommended answer:** Accept local storage for the bounded pilot only if
  MD-010 through MD-012 are satisfied.
- **Management decision:** [ ]
- **Owner / approver:** Operations Approver: TBD; Security Approver: TBD.

## MD-010 — Pilot Backup Policy

- **Decision ID:** MD-010
- **Topic:** Approve coordinated PostgreSQL and uploaded-file backups, an
  encrypted off-site copy, and a documented restore procedure.
- **Why management needs to decide:** Persistent volumes alone are not backups;
  database/file inconsistency can prevent recovery.
- **Current recommendation:** Automated coordinated backups, integrity records,
  encrypted off-site storage, failure escalation, and restore documentation.
- **Alternatives:** Stronger managed backup/PITR; internal-only pilot without
  customer persistence; defer external pilot.
- **Impact of decision:** Sets the minimum data-loss and host-failure protection
  required before measured customers.
- **Recommended answer:** Approve the proposed pilot backup policy as a Phase 2
  prerequisite.
- **Management decision:** [ ]
- **Owner / approver:** Operations Approver: TBD; Security Approver: TBD.

## MD-011 — Pilot RPO and RTO

- **Decision ID:** MD-011
- **Topic:** Approve or replace proposed pilot RPO 24 hours and RTO 8 hours.
- **Why management needs to decide:** Recovery investment and customer
  expectations require accepted maximum data loss and restoration time.
- **Current recommendation:** RPO 24 hours; RTO 8 hours for minimum pilot
  service. These are proposals, not measured facts or production objectives.
- **Alternatives:** Tighter objectives with higher cost; looser explicitly
  accepted objectives; no external pilot until measured.
- **Impact of decision:** Determines backup frequency, recovery procedure,
  support commitments, and pilot risk.
- **Recommended answer:** Approve 24-hour RPO / 8-hour RTO provisionally, then
  validate through a restore test before customer admission.
- **Management decision:** [ ]
- **Owner / approver:** Management Approver: TBD; Operations Approver: TBD.

## MD-012 — Backup Retention and Restore Testing

- **Decision ID:** MD-012
- **Topic:** Set backup retention, restore-test frequency, and accountable
  operator.
- **Why management needs to decide:** A backup without retention ownership and
  tested restoration does not establish recoverability.
- **Current recommendation:** Retain multiple recovery points including at least
  30 days of daily pilot backups; test before external pilot and quarterly
  thereafter; name one accountable Operations owner. The 30-day/quarterly
  values are proposals.
- **Alternatives:** Different approved retention/frequency based on contract,
  cost, deletion obligations, and risk; managed continuous recovery.
- **Impact of decision:** Affects storage cost, deletion/backup expiry, operator
  workload, and confidence in MD-011.
- **Recommended answer:** Approve or replace the proposed values and name the
  accountable operator before Phase 2 exit.
- **Management decision:** [ ]
- **Owner / approver:** Accountable Operator: TBD; Operations Approver: TBD;
  Security Approver: TBD.

## MD-013 — Pilot Capacity Assumption

- **Decision ID:** MD-013
- **Topic:** Approve Pilot 10 customers now; retain Growth 100 and Scale 1,000
  as planning scenarios only.
- **Why management needs to decide:** The pilot needs a bounded support and
  measurement envelope without implying unverified scale.
- **Current recommendation:** Approve only the 10-customer Pilot scenario now.
  Use 100/1,000 solely to define measurements and architecture revisit points.
- **Alternatives:** Smaller pilot; another bounded pilot maximum; approve no
  external capacity until benchmarks exist.
- **Impact of decision:** Controls admission, test workloads, support staffing,
  provider limits, and storage/backup planning.
- **Recommended answer:** Approve 10 customers as a limit, not a capacity claim.
- **Management decision:** [ ]
- **Owner / approver:** Management/Product Approver: TBD; Operations Approver:
  TBD.

## MD-014 — Cost Governance

- **Decision ID:** MD-014
- **Topic:** Define reporting currency, approved provider price inputs, budget
  owner, budget threshold, cost/conversation target, and AI cost/revenue target
  if applicable.
- **Why management needs to decide:** Technical telemetry cannot determine
  commercial targets or acceptable spend.
- **Current recommendation:** Name a budget owner; use contracted DeepSeek and
  Voyage rates with effective dates; select one reporting currency; set a pilot
  spend ceiling and alert threshold; treat cost/conversation and AI
  cost/revenue as measured targets, with `N/A` explicitly allowed where revenue
  is not yet attributable.
- **Alternatives:** Finance-owned monthly review without automated threshold;
  product-specific budgets; no revenue ratio during pilot.
- **Impact of decision:** Enables pilot cost acceptance, anomaly response, and
  later pricing decisions without inventing provider prices.
- **Recommended answer:** Management/Finance completes the six inputs before
  measured customer testing.
- **Management decision:** [ ]
- **Owner / approver:** Budget Owner: TBD; Finance/Management Approver: TBD.

## MD-015 — Security Risk Acceptance

- **Decision ID:** MD-015
- **Topic:** Decide pilot malware scanning, operator/admin access, break-glass
  access, incident ownership, and accepted residual risks.
- **Why management needs to decide:** Current controls are strong at application
  boundaries but do not eliminate malicious-file, privileged-operator,
  single-host, manual-classification, or provider exposure risks.
- **Current recommendation:** Restrict pilot file types and owners; require
  malware scanning before external untrusted uploads or explicitly accept a
  tightly bounded exception; name least-privilege operators; document
  time-limited logged break-glass access; name Security and Operations incident
  owners; record accepted risks and expiry/review dates.
- **Alternatives:** Internal trusted files only; deploy scanning before pilot;
  external security review; defer external customers.
- **Impact of decision:** Determines eligible customers/files, operator process,
  incident response, and residual-risk accountability.
- **Recommended answer:** Approve a written pilot risk register with named
  owners and conditions; do not rely on implicit acceptance.
- **Management decision:** [ ]
- **Owner / approver:** Security Approver: TBD; Operations Approver: TBD;
  Management Risk Owner: TBD.

## MD-016 — Phase 1 Exit Gate

- **Decision ID:** MD-016
- **Topic:** Formal Architecture v1.0 decision.
- **Why management needs to decide:** Phase 2 should proceed under a recorded
  architecture and governance baseline rather than unresolved assumptions.
- **Current recommendation:** Decide only after MD-001 through MD-015 are
  answered or recorded as explicit conditions with owners and due dates.
- **Alternatives:** Approve; approve with conditions; return for changes.
- **Impact of decision:** Closes or keeps open Phase 1. It does not approve
  Production topology, Kubernetes, microservices, production object storage,
  or production DR.
- **Recommended answer:** Approve with conditions only where every condition
  has a named owner, due date, and effect on Phase 2 customer admission.
- **Management decision:** [ ]
- **Owner / approver:** Management Approver: TBD; Architecture Owner: TBD.

### Architecture v1.0

- [ ] **APPROVED**
- [ ] **APPROVED WITH CONDITIONS**
- [ ] **CHANGES REQUIRED**

**Conditions / Notes:**

______________________________________________________________________________

______________________________________________________________________________

Detailed review checklist:
`docs/architecture/architecture-v1-approval-checklist.md`.
