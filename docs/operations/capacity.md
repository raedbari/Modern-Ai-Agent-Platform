# Capacity Planning

## Status and Method

This document defines scenarios and required measurements. It contains no
benchmark result and makes no capacity claim. Architecture changes follow:

```text
Measure -> find bottleneck -> change architecture -> measure again
```

## Planning Scenarios

| Scenario | Customers | Purpose |
|---|---:|---|
| Pilot | 10 | Validate correctness, quality, isolation, latency, cost, and operations |
| Growth | 100 | Plan the first evidence-based scaling changes |
| Scale | 1,000 | Long-range model; not a current commitment |

## Variables Required for Every Scenario

| Variable | Required measurement |
|---|---|
| Concurrent users | Peak and sustained authenticated/Widget concurrency |
| Documents/customer | Count, type, size distribution, update/delete frequency |
| Chunks/vectors | Per document, customer, and total; index growth |
| Conversations/month | Customer, agent, channel, and peak-time distribution |
| Tokens/conversation | Input, evidence, and output distribution |
| Embedding calls | Document and query calls, text volume, batch size, retries |
| Rerank calls | Candidates sent, results retained, failures, retries |
| Storage/database growth | PostgreSQL, indexes, WAL/backups, original files, Redis |
| Worker throughput | Jobs/time, queue depth, processing latency, failures, recovery |
| Latency | P50/P95/P99 by bootstrap, chat, retrieval, provider, upload, job |

Also record error rate, provider availability, CPU, memory, disk I/O, network,
database connections, cache behavior, and operational intervention.

## Pilot: 10 Customers

The pilot must establish actual ranges for all variables above using controlled
datasets and limited real traffic. Acceptance thresholds for latency, error
rate, worker backlog, storage headroom, and cost are TBD. The current Compose
topology is a candidate to measure, not a guaranteed capacity result.

## Growth: 100 Customers

Project measured pilot distributions using stated growth assumptions. Test
database connections, vector query latency, worker backlog, provider quotas,
storage/backup duration, API concurrency, and operator load. Do not extrapolate
only from customer count; document and conversation distributions can dominate.

## Scale: 1,000 Customers

Use verified Growth measurements and workload segmentation. Evaluate tenant
concentration, regulated isolation, horizontal API behavior, worker partitioning,
database/vector limits, backup/restore duration, observability volume, and cost.
This scenario does not authorize Kubernetes, microservices, or a dedicated
vector database.

## Architecture Exit Points

```text
Single Server
  -> Separate Database, only if reliability/resource/security evidence requires
  -> Separate Workers, only if queue throughput or isolation requires
  -> Horizontal API, only if measured concurrency/availability requires
  -> Dedicated Vector Layer, only after benchmarked pgvector limits
```

Steps are not mandatory or strictly coupled. For example, workers may separate
before the database when queue evidence supports it. Every exit requires a
decision record, rollback plan, cost comparison, and before/after measurement.

## Data Collection Owners

- Agent Runtime: tokens, provider calls, retrieval/rerank counts and latency.
- Knowledge Platform: documents, chunks, vectors, jobs and storage growth.
- Shared Observability: request concurrency, errors, resource and latency data.
- Operations: host/database/backup capacity and recovery duration.
- Product: active users, customer usage, conversations and support burden.

Named owners and approved thresholds are TBD.
