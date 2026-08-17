# TX AI Lab Controlled Pilot Threat Model

## Scope

This proposed threat model covers the Modular Monolith, PostgreSQL/pgvector,
Redis, ingestion worker, local pilot upload storage, DeepSeek, Voyage,
Athkachatbots customer/admin APIs, and public Widget. It records current
controls and gaps; it does not assert production readiness.

## Security Invariants

- Tenant data never crosses the trusted tenant boundary.
- Product and platform privileges follow least privilege.
- Widget credentials cannot become tenant-user, API-key, or admin authority.
- Only tenant-filtered evidence reaches reranking and generation.
- Secrets never enter source control, API responses, prompts, or ordinary logs.
- Deletion covers metadata, files, chunks, embeddings, indexes, and applicable
  operational copies.

## Threat Register

| Asset | Threat | Existing control | Current gap | Future mitigation |
|---|---|---|---|---|
| Tenant knowledge, conversations, agents | Cross-tenant leakage through a missing filter or forged identifier | Trusted auth contexts, tenant-scoped repositories, composite relationships, cross-tenant tests, tenant-first retrieval | Not every future query is mechanically proven; shared DB has broad operator blast radius | Expand boundary/static checks, database policy evaluation, recurring isolation tests, access reviews |
| Tenant/admin resources | IDOR using another tenant's resource ID | Server-resolved tenant context, ownership queries, hidden/forbidden responses, API tests | New endpoints can omit consistent ownership checks | Central authorization helpers, endpoint review checklist, negative contract tests |
| Admin and tenant privileges | Role or session privilege escalation | Admin RBAC, tenant roles, live membership validation, short-lived JWTs, session revocation tests | Formal access-review and break-glass procedures are absent | Periodic access reviews, least-privilege role review, operator MFA/SSO where approved |
| Public Widget and conversations | Stolen/replayed Widget token, forged claims, Origin abuse, cross-session conversation access | Short-lived signed token, audience/claim validation, exact normalized Origin, allow-list recheck, session-bound conversations, rate limits | Token theft within an allowed site and CSP/integration posture are not fully governed | CSP/integration guidance, tighter lifetime based on measurement, anomaly telemetry, rotation/incident process |
| Agent prompt and response integrity | Prompt injection from user input | Evidence is delimited as untrusted data, knowledge modes, answerability/fallback behavior | No comprehensive injection evaluator or tool sandbox because tools are not yet generalised | Injection test corpus, policy checks, citation validation, tool allow-lists if tools are introduced |
| Knowledge chunks and RAG | Retrieval injection or malicious instructions in uploaded content | Tenant/agent scoping, bounded evidence, required-mode fallback, sources | No content classification, provenance approval workflow, or injection scanning | Approval lifecycle, provenance metadata, retrieval-injection evaluation and content policy |
| API/worker host and parsers | Malicious files, parser exploits, decompression abuse, malware | File type/size validation, bounded parsers, worker separation, safe error handling | No malware scanner, sandboxed parser service, OCR security policy, or quarantine state | Quarantine/scanning based on risk, parser hardening, approved file policy, resource limits |
| Provider/API credentials and customer secrets | Secret exposure in Git, logs, errors, prompts, backups | Environment-based secrets, secret CI guard, masked secret types, sanitized provider errors | Rotation, vaulting, backup-secret handling, and incident procedures are incomplete | Managed secret store, rotation schedule, least-privilege credentials, recovery drills |
| Customer and provider data | External provider receives disallowed or excessive content | Provider adapters, tenant filtering before rerank, minimum rerank payload, no credentials in provider input | No automated classification/redaction or approved provider register | Enforce provider-data policy, request decision record, redaction/blocking, contract review |
| API, Widget, providers, worker | Denial of service, quota exhaustion, rate abuse | Widget and selected API rate limits, upload size limits, bounded retrieval/output, retries, worker jobs | No tenant quotas, global budget control, load baseline, or alerting | Per-tenant quotas, cost budgets, queue/backpressure metrics, load tests and alerts |
| Knowledge and conversations | Deletion or retention failure leaves files, chunks, embeddings, caches, backups, or messages | Knowledge deletion paths, storage keys, audit foundations, repository tests | Retention policy and backup deletion semantics are not defined; conversations lack general retention governance | Approved retention schedule, deletion verification, backup-expiry policy, customer deletion evidence |
| Database, uploads, service continuity | Host loss or corrupt backup | Persistent Compose volumes and health checks | Backups, off-site copy, RPO/RTO, and restore evidence are not yet established | Pilot backup plan, off-site encrypted copy, restore drills, production DR plan |
| Supply chain and deployments | Vulnerable dependency or unauthorized release | Locked dependencies, CI tests, CodeQL workflow, architecture/secret guards | Formal release approval, SBOM, patch SLA, signing, and rollback evidence are incomplete | Dependency policy, SBOM/signing decision, staging, release/rollback runbook |

## Trust-Boundary Review Requirements

Any new endpoint, provider, parser, storage adapter, background job, or product
must document identity, tenant resolution, data classification, authorization,
provider exposure, deletion behavior, telemetry, and failure mode. A future
service split does not replace these controls.

## Unresolved Approval Items

- Risk owners and accepted residual risk.
- Classification taxonomy and permitted provider matrix.
- Pilot operator access and break-glass process.
- Malware-scanning threshold and accepted pilot file types.
- Backup encryption, RPO/RTO, and incident-notification expectations.
