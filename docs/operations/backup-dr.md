# Backup and Disaster Recovery

## Status

Proposed Architecture v1.0 assumptions for management and Operations review.
The repository does not currently provide evidence of scheduled backups,
off-site copies, or successful restore tests. This document must not be used as
evidence that those controls exist.

## Scope

Backup scope includes:

- PostgreSQL metadata, authentication data, audit records, conversations,
  knowledge records, chunks, and pgvector embeddings;
- original/retained uploads and derived file objects;
- deployment configuration required for recovery, excluding secrets from
  ordinary source backups;
- secret identifiers, recovery procedure, and separately protected recovery
  material;
- migration versions, application image/source revision, and operational
  runbooks needed to reproduce the service.

Redis is currently operational state. Whether any Redis data requires backup
must be decided per use; it must not be assumed to be the authoritative store.

## Proposed Controlled Pilot Strategy

1. Take an automated PostgreSQL logical or physical backup at least daily.
2. Back up the local upload volume on a coordinated schedule so database
   references and file objects can be reconciled.
3. Encrypt backup data and transfer at least one copy off the pilot host.
4. Retain multiple recovery points under an approved retention schedule.
5. Record backup time, scope, result, checksum/integrity result, and operator or
   automation identity.
6. Alert or escalate on missed and failed backups.
7. Execute a documented restore into an isolated environment before admitting
   measured customers, then repeat on an approved schedule.

Tooling, destination, retention duration, encryption/key custody, and operator
ownership are TBD.

## Proposed Pilot RPO / RTO Assumptions

- **Proposed pilot RPO:** 24 hours maximum data loss.
- **Proposed pilot RTO:** 8 hours to restore minimum customer service.

These are planning assumptions only. Management, Operations, Security, and
pilot customer expectations must approve or replace them. They are not
production objectives and have not been demonstrated.

## Restore Test Requirement

A restore test is successful only when the team can:

- restore PostgreSQL to a known recovery point;
- restore and reconcile retained uploads;
- apply migrations safely;
- authenticate approved users;
- retrieve tenant-scoped knowledge and complete a grounded chat;
- confirm cross-tenant isolation;
- verify Widget bootstrap/chat where included in the recovery scope;
- record elapsed time, data-loss point, missing objects, and corrective actions.

Backups without tested restoration do not satisfy the Phase 2 exit gate.

## Secrets and Recovery

Secrets must not be stored in Git or ordinary database/file backups. Recovery
requires a separately protected inventory and process for database credentials,
JWT/Widget signing keys, admin credentials, provider keys, backup encryption
keys, TLS material, and rotation after suspected compromise. Loss of signing
keys can invalidate sessions; restoration of old keys can revive risk and must
follow an approved incident decision.

## Controlled Pilot Limitations

- Local upload storage and a single host create a common failure domain.
- Daily backup may lose up to the proposed RPO.
- Recovery is operator-driven until automation is approved.
- No claim of high availability, PITR, immutable backup, or multi-region DR is
  made by this document.

## Production Target — Not Yet Approved

Production approval requires measured RPO/RTO, automated encrypted off-site
backups, defined PITR/WAL policy where needed, object-storage protection,
immutable or protected copies where justified, regular restore drills, secret
recovery, incident ownership, and a full-host failure plan. Production values
must be set from business impact and pilot evidence, not copied automatically
from the pilot assumptions.

## Open Decisions

- Backup technology and off-site destination.
- Retention and immutable-copy requirements.
- Final pilot and production RPO/RTO.
- Backup deletion behavior for customer deletion and legal hold.
- Restore-test frequency and accountable operator.
