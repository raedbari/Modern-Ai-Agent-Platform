# Total Cost of Ownership Model

## Status

Proposed cost-governance framework. It defines required inputs and formulas but
contains no approved provider price, forecast, budget, or measured result.

## Cost Categories

1. **Infrastructure:** compute, database, Redis, workers, environments, and
   managed-service charges.
2. **Generation:** DeepSeek input/output token usage, retries, failed calls, and
   any future approved generation provider.
3. **Embeddings:** Voyage document/query text volume, calls, batches, retries,
   and re-embedding after updates.
4. **Reranking:** Voyage rerank requests, candidates, retries, and failures.
5. **Storage:** PostgreSQL, pgvector indexes, original/derived files, retained
   datasets, logs, and growth.
6. **Backups:** backup storage, transfer, retention, restore environments, and
   restore-test labor.
7. **Monitoring:** logs, metrics, traces, dashboards, alerts, and retention.
8. **Network:** ingress/egress, provider traffic, customer traffic, DNS/TLS, and
   content delivery where applicable.
9. **Security:** secret management, scanning, assessments, certificates,
   incident tooling, and compliance controls.
10. **Operations:** engineering/on-call time, support, deployments, incidents,
    backup reviews, and customer interventions.

## Required Input Variables

| Input | Symbol/example | Approval source |
|---|---|---|
| Fixed monthly platform cost | `fixed_platform_cost` | Operations/Finance |
| Generation input/output units and rates | `gen_input_units`, `gen_output_units`, `gen_rates` | Provider contract; TBD |
| Embedding units and rate | `embedding_units`, `embedding_rate` | Provider contract; TBD |
| Rerank units and rate | `rerank_units`, `rerank_rate` | Provider contract; TBD |
| Storage by class and rate | `storage_gb_class`, `storage_rate_class` | Vendor/Operations; TBD |
| Backup/monitoring/network/security cost | category variables | Vendor/Operations; TBD |
| Operations hours and loaded rate | `ops_hours`, `ops_rate` | Management/Finance; TBD |
| Active customers/users/conversations | measured denominators | Product telemetry |
| Revenue attributed to AI service | `ai_revenue` | Finance/Product; TBD |

No placeholder should silently default to zero in an approval report. Missing
inputs must be shown as unknown.

## Core Calculations

```text
total_cost = infrastructure
           + generation
           + embeddings
           + reranking
           + storage
           + backups
           + monitoring
           + network
           + security
           + operations

cost_per_customer = total_cost / active_customers
cost_per_active_user = total_cost / active_users
cost_per_conversation = total_cost / completed_conversations
cost_per_1m_tokens = attributable_generation_cost / total_tokens * 1,000,000
ai_cost_to_revenue = attributable_ai_cost / ai_revenue
```

Division-by-zero and incomplete-period handling must be explicit.

## Allocation Principles

- Separate fixed shared cost from directly attributable provider/storage use.
- Attribute usage by tenant, product, agent, provider/model, and period where
  policy permits.
- Record failed/retried provider calls because they consume capacity or money.
- Keep estimates distinguishable from invoiced actuals.
- Do not expose one tenant's usage or commercial data to another.
- Do not optimize solely for unit cost at the expense of quality, security, or
  reliability.

## Pilot Reporting

The measured pilot should report cost/customer, cost/active user,
cost/conversation, cost/1M tokens, and AI cost/revenue with the input period,
currency, source, tax treatment, estimate confidence, and excluded categories.

## Unresolved Decisions

- Approved currency and reporting period.
- Provider contract prices and volume tiers.
- Shared-cost allocation method.
- Labor-cost treatment.
- Budget and anomaly thresholds.
- Revenue attribution and acceptable AI cost/revenue target.
