# Evaluation architecture

The Sprint 1 evaluation platform is file-backed and version-aware. A JSON
metadata manifest identifies dataset name, owner, domain, version, lifecycle
status, and classification; JSONL contains independently validated records.
`load_evaluation_dataset` combines both into an immutable validated dataset.

Each run records this reproducibility chain:

```text
dataset version -> agent version -> prompt version -> knowledge version
                -> model provider/model -> case results -> report
```

Cases contain trusted synthetic tenant and agent scopes. Evaluation is not an
authorization bypass: the evaluated target must use the same tenant-scoped
retrieval path as production. Golden Questions v1 uses controlled fixtures and
includes answerable, unanswerable, misleading-evidence, multi-chunk,
insufficient-evidence, tenant-isolation, Arabic, dialect, and injection cases.

`EvaluationRun` ties a run ID and timestamps to its immutable configuration,
case results, status, and aggregate metrics. `ExperimentComparison` is the
minimal A/B record. It compares two immutable run
configurations and their measured aggregates; it does not select a winner or
change production configuration.

`EvaluationRunner` invokes the same compiled `ChatWorkflow` used by chat. Its
retrieval dependency is the production `RetrievalService`, so embedding,
tenant/agent filtering, reranking, evidence construction, answerability,
generation, and citation validation are observed rather than simulated by a
second evaluation pipeline.

Golden Questions v1 has exactly 20 records plus controlled, tenant/agent-scoped
knowledge fixtures. Tests inject deterministic generation, embedding, and
reranking providers; no paid provider is called.

`knowledge_version` remains optional. Knowledge Platform is authoritative for
real lifecycle/version identifiers. Until its production contract exposes an
authoritative identifier, Agent Runtime propagates a supplied identifier but
does not create or own one.
