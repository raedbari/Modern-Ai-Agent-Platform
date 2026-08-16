# Controlled Pilot Observability

## Scope

The controlled pilot uses a small Platform Core telemetry boundary around the
existing Athkachatbots production chat workflow. It is intended to measure
pilot behaviour without adding a dashboard, collector, message broker, or a
second database. It is not a production-scale observability platform.

The chat endpoint assigns one UUID request ID to each authenticated chat
request. A canonical UUID supplied in `X-Request-ID` is preserved; missing or
invalid input is replaced with a new server-generated UUID. The ID is passed
through the provider-independent AI runtime context and returned as the
`X-Request-ID` response header. Authorized Widget responses expose that header
through CORS without changing the JSON response contract.

## AI telemetry event

Shared Platform owns the provider-independent `AITelemetryEvent`, replaceable
`TelemetrySink` port, request-correlation rules, privacy constraints, and sink
adapters. Agent Runtime owns the workflow instrumentation that supplies
provider, model, retrieval, rerank, source, token, latency, status, version,
and sanitized failure observations to that shared boundary.

Exactly one event is emitted by `ChatWorkflow` for each instrumented workflow
execution, including failed attempts. `ChatService` establishes trusted
correlation and tenant/product/agent/conversation context, persists the turn,
and invokes the workflow; it does not construct another AI telemetry event.
The lower-level generation provider runtime also does not own the final chat
request event.

The event can capture:

- `request_id`, `tenant_id`, `product_id`, `agent_id`, and `conversation_id`
- provider and returned model identifiers
- prompt and knowledge versions when a future owning contract supplies them
- retrieval, rerank, and returned source counts when known
- answer status and a bounded exception class name for failures
- input and output token counts reported by the generation provider
- end-to-end chat-service latency in milliseconds and a UTC timestamp

Tenant identity is required on every event. Conversation identity is retained
when it is supplied or successfully allocated, including requests that later
fail. Events do not provide an arbitrary metadata bag.

## Deliberate exclusions

The event schema has no fields for raw prompts, system instructions, message
history, model answers, customer documents or excerpts, API keys, bearer
tokens, secrets, or unrestricted message content. Sink failures are logged
against only request and tenant IDs and do not alter the customer response.

The telemetry record is operational metadata, not a replacement for the
separately governed conversation store. Existing conversation persistence is
unchanged.

## Pilot sink

`StructuredLoggingTelemetrySink` is the default pilot adapter. It writes one
compact JSON object per validated event through the existing application
logging infrastructure under the `maap.pilot_telemetry` logger. Deployment log
retention and access controls therefore govern the pilot records.

`InMemoryTelemetrySink` demonstrates replacement at the port and supports
tests without external infrastructure. Telemetry delivery is best effort for
the pilot: an unavailable sink must not fail a customer chat request.

## Evaluation and production evolution

Evaluation owns evaluation cases, metrics, and reports. When it needs runtime
observations, it executes the instrumented workflow with the same canonical
telemetry boundary; it does not define a second general event or sink.

Current production composition does not yet supply prompt version, knowledge
version, or an exact rerank count, so those values remain `null`. Retrieval
count currently means chunks returned to the chat workflow; source count means
citations attached to the final answer. Provider is supplied by trusted
application composition rather than inferred by the sink.

A later measured need may justify durable repository-compatible storage,
aggregation, retention policy automation, alerting, or standard telemetry
export. Such evolution should replace the sink adapter and preserve the event
privacy and tenant-isolation contract.

Cost fields are intentionally unresolved. No token prices, inferred charges,
estimated cost, currency, or infrastructure allocation are emitted until
approved provider pricing sources and cost ownership rules exist.
