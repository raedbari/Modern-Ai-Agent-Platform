# Agent Runtime boundary

The Agent Runtime is a provider-independent gateway plus the evidence-first
chat workflow. Product routes resolve trusted tenant and agent configuration;
the workflow applies knowledge policy; provider ports perform generation,
embedding, and reranking. Providers never decide tenancy or product policy.

## Agent field classification

| Target field | Sprint 1 classification | Representation |
|---|---|---|
| `tenant_id` | existing | Agent domain and database models |
| `name` | existing | Agent database model |
| `system_prompt` | existing | Agent database model |
| `knowledge_policy` | existing | `knowledge_mode` |
| `prompt_version` | add-now | Agent domain/database models and runtime context |
| `product_id` | add-now at runtime boundary | optional `RuntimeContext.product_id`; persistence remains Platform Core-owned |
| `role` | design-later | no pilot requirement |
| `status` | design-later | lifecycle ownership requires a cross-team contract |
| `model_policy` | add-now boundary | `ModelPolicy`; startup configuration remains the implementation |
| `tool_policy` | design-later | tools are outside Sprint 1 |
| `memory_policy` | design-later | memory is outside Sprint 1 |
| `budget_policy` | design-later implementation | protocol only |
| `safety_policy` | design-later implementation | protocol only |

## Runtime invariants

- Every retrieval is explicitly scoped by trusted `tenant_id` and `agent_id`.
- Required mode never calls generation without evidence.
- Evidence is bounded and treated as untrusted data.
- A grounded result must cite at least one supplied source and may not cite an
  unknown source identifier.
- Provider exceptions are normalized by the calling service; telemetry failure
  never changes the user request outcome.
- Runtime context carries prompt and knowledge versions when known.

The workflow owns answerability and citation validation. The provider gateway
owns provider invocation and its normalized telemetry emission point.
