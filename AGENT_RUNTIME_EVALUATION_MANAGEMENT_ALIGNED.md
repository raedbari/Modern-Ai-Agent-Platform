# Sprint 1 — Agent Runtime, Prompt Foundation & Evaluation Platform

## Owner
Developer 3

## Branch
`feat/agent-runtime-evaluation-foundation`

## Baseline SHA
`a6550335c80be836dd95fac8b81eff783c6eae8e`

## Mission
Evolve the current query-time RAG implementation into the first reusable **TX AI Lab Agent Runtime Platform** and establish a real **Evaluation Platform foundation**.

DeepSeek is the current generation provider.
Voyage is the current embedding/reranking provider.
The architecture must not depend on either provider as a permanent hard-coded assumption.

---

## 1. Generic Agent Runtime Boundary

Target Agent concept:

```text
Agent
├── tenant_id
├── product_id
├── name
├── role
├── status
├── system_prompt
├── prompt_version
├── knowledge_policy
├── model_policy
├── tool_policy
├── memory_policy
├── budget_policy
└── safety_policy
```

### Sprint Requirement
Do not add all fields blindly.

Audit current Agent model and classify each target field:

```text
existing
add-now
design-later
```

Implement the minimum reusable foundation required to prevent Athkachatbots-specific runtime coupling.

Document deferred fields.

---

## 2. Prompt Versioning Foundation

Create a design and minimum implementation for:

```text
Prompt
├── Version 1
├── Version 2
├── Version 3
└── Active Version
```

At minimum, important runtime/evaluation records should be able to identify:

```text
agent_id
prompt_version
model/provider
knowledge_version or knowledge context identifier
```

Do not build a complex prompt CMS unless required.

Create documentation under:

```text
docs/agents/
├── runtime.md
├── prompt-versioning.md
└── provider-strategy.md
```

---

## 3. Provider Abstraction

Required interfaces:

```text
GenerationProvider
EmbeddingProvider
RerankProvider
```

Correct architecture:

```text
Agent Runtime
→ GenerationProvider
→ DeepSeek implementation
```

```text
Agent Runtime
→ EmbeddingProvider
→ Voyage implementation
```

```text
Agent Runtime
→ RerankProvider
→ Voyage implementation
```

Provider details must not leak through runtime business logic.

### Current Providers
- Generation: DeepSeek
- Embeddings: Voyage
- Rerank: Voyage

Provider selection should be configuration/policy, not architecture.

---

## 4. Model Policy / Routing Foundation

Management target considers routing based on:

```text
quality
latency
cost
availability
data classification
tenant policy
```

### Sprint Requirement
Do not implement a speculative multi-provider router.

Instead:
- define a `ModelPolicy`/routing boundary;
- document decision inputs;
- keep current DeepSeek path working;
- make future provider addition possible without runtime rewrite.

Provider fallback can remain deferred unless already practical.

---

## 5. Required RAG Runtime

```text
Question
↓
Tenant / Agent Scope
↓
Permission Check
↓
Voyage Query Embedding
↓
pgvector Top 20
↓
Voyage rerank-2.5
↓
Top 5
↓
Evidence Selection
↓
Answerability Check
↓
DeepSeek
↓
Citation Validation
↓
Grounded Response
```

### Mandatory Rules
- no cross-tenant retrieval
- no generation from unsupported knowledge in Required mode
- source/citation metadata preserved
- answerability decision explicit
- provider failure predictable

---

## 6. Knowledge Modes Foundation

Support/document policy semantics:

### Required
```text
No evidence
→ no factual answer
→ safe fallback
```

### Preferred
```text
Evidence available → use it
No evidence → model may answer if product policy permits
```

### Disabled
```text
No knowledge retrieval
```

### Sprint Requirement
At minimum, implement/document `Required` correctly.
Other modes may be represented as policy contracts if not yet needed.

---

## 7. Evaluation Platform Data Model

This must be more than a test file.

Design/create first reusable evaluation domain:

```text
Dataset
├── name
├── owner
├── domain
├── version
├── status
├── classification
└── records
```

Golden Question target fields:

```text
question
expected_answer / expected_facts
expected_source
allowed_variations
forbidden_claims
category
difficulty
language
dialect
answerable
tenant
```

Create:

```text
docs/evaluation/
├── evaluation-architecture.md
└── metrics.md
```

The data model may begin file-backed for Sprint 1 if persistence is not yet justified, but the schema must be reusable and version-aware.

---

## 8. Golden Questions v1

Start with **20 Golden Questions**.

Include:
- answerable
- unanswerable
- misleading-similar evidence
- multiple relevant chunks
- insufficient evidence
- tenant isolation
- Arabic examples if product scope requires Arabic
- dialect examples if relevant to pilot

Do not invent production/customer facts. Use controlled test fixtures.

---

## 9. Evaluation Runner

Required evaluation flow:

```text
Dataset Version
↓
Agent Version
↓
Prompt Version
↓
Knowledge Version
↓
Model / Provider
↓
Run
↓
Metrics
```

Minimum first metrics:

```text
Retrieval Hit
Top-K Source Presence
Rerank Position
Groundedness
Correct Refusal
Citation Presence/Accuracy where feasible
Latency
Failure Rate
Token Usage if exposed
Estimated Cost if exposed
```

If a metric cannot yet be measured reliably, report `NOT MEASURED`; do not fake it.

---

## 10. Experiment Foundation

Do not build a full experiment platform yet.

Define a minimal comparison record:

```text
Experiment
Dataset Version
Configuration A
Configuration B
Metrics A
Metrics B
```

This is enough to support future comparison of:
- prompts
- providers
- retrieval settings

---

## 11. Telemetry Contract

Coordinate with Platform Core on AI request telemetry:

```text
request_id
tenant_id
product_id
agent_id
conversation_id
model_provider
model_name
prompt_version
knowledge_version
retrieval_count
rerank_count
source_count
answer_status
input_tokens
output_tokens
latency_ms
estimated_cost
error_type
timestamp
```

You own runtime emission points.
Platform Core owns shared observability architecture/governance.

---

## Files / Areas to Inspect

```text
backend/app/ai/chat_workflow.py
backend/app/ai/contracts.py
backend/app/ai/ports.py
backend/app/ai/runtime.py
backend/app/ai/rerank.py
backend/app/ai/providers/deepseek.py
backend/app/ai/providers/voyage.py
backend/app/services/knowledge/retrieval_service.py
backend/app/db/models.py
backend/tests/test_ai_providers.py
backend/tests/test_ai_runtime.py
backend/tests/test_chat_workflow.py
backend/tests/test_grounded_chat.py
backend/tests/test_rag_filter.py
backend/tests/test_retrieval_service.py
backend/tests/test_pipeline_integration.py
backend/tests/test_voyage_provider.py
docs/evaluation/
docs/agents/
```

Follow actual repository filenames if some differ.

---

## Cross-Team Boundary With Developer 2

Developer 2 owns:
- knowledge version lifecycle
- chunks
- document embeddings
- persistence

Developer 3 owns:
- query-time retrieval orchestration
- rerank
- answerability
- generation
- evaluation

Shared contracts:
- retrieval result
- source metadata
- knowledge version
- tenant/product scope
- embedding configuration

---

## Forbidden Changes

Do NOT:
- implement document replacement
- redesign Knowledge CRUD
- bypass tenant filters for evaluation
- add a second Voyage implementation
- hard-code runtime directly to DeepSeek HTTP internals
- add Ollama to target architecture
- build speculative multi-provider routing complexity
- add microservices
- add Kubernetes
- add Billing
- move all files to target folder structure in one Sprint
- train/fine-tune models

---

## Required Tests

```text
[ ] query embedding uses query semantics
[ ] tenant-scoped retrieval
[ ] Top 20 candidate flow
[ ] rerank-2.5 invocation
[ ] Top 5 evidence selection
[ ] source metadata preserved
[ ] Required-mode no-evidence refusal
[ ] answerability behavior
[ ] DeepSeek grounded generation
[ ] provider failure behavior
[ ] provider interfaces tested
[ ] prompt version captured
[ ] 20 Golden Questions load
[ ] evaluation runner executes
[ ] retrieval metric produced
[ ] rerank metric produced
[ ] refusal metric produced
[ ] latency measured
[ ] tenant-isolation evaluation case
```

---

## Definition of Done

```text
[ ] Agent Runtime boundary documented
[ ] current Agent model mapped to target fields
[ ] prompt versioning foundation exists
[ ] provider abstractions clean
[ ] ModelPolicy boundary documented/implemented minimally
[ ] Required knowledge mode works
[ ] RAG path proven
[ ] Evaluation data model exists
[ ] 20 Golden Questions exist
[ ] evaluation runner is repeatable
[ ] baseline metrics produced
[ ] telemetry emission points identified/implemented
[ ] no cross-tenant retrieval
[ ] relevant tests green
```

---

## PR Title
`feat(ai): establish reusable agent runtime and evaluation platform foundation`

## PR Must Include
- Agent target/current mapping
- prompt-versioning decisions
- provider abstraction changes
- runtime pipeline proof
- knowledge mode behavior
- evaluation schema
- golden-question dataset
- evaluation results
- metrics limitations
- telemetry impact
- tests
