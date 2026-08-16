# Evaluation metrics

Metrics are deterministic where the runtime exposes sufficient evidence. A
missing observation is `not_measured`, never zero and never an inferred pass.

| Metric | Sprint 1 definition |
|---|---|
| Retrieval hit | at least one eligible chunk was returned |
| Top-K source presence | an expected source occurs in selected evidence |
| Rerank position | expected/top source position after reranking |
| Groundedness | factual output is supported by supplied evidence |
| Correct refusal | an unanswerable case ends in insufficient-knowledge status |
| Citation presence | output contains at least one supplied citation identifier |
| Citation accuracy | every emitted citation identifies supplied evidence |
| Latency | wall-clock duration around the evaluated operation |
| Failure rate | error cases divided by all cases |
| Token usage | provider-reported input and output token counts |
| Estimated cost | measured only when a governed price table is supplied |

The production retrieval result exposes candidate and successful rerank-result
counts to the workflow without storing Knowledge lifecycle state. Evaluation
records supplied document IDs separately from actually cited document IDs and
unknown citation labels. Expected-source citation accuracy therefore requires
the expected document to be both supplied and cited.

String/language checks are smoke signals, not semantic correctness measures.
Substring checks must not be reported as groundedness. Human or model judging
can be added later only with judge identity/version and limitations recorded.
