# AI Provider Data Policy

## Purpose

Define the proposed decision process before data is transmitted to an external
AI provider. This document is governance direction, not a claim that automated
classification, redaction, or policy enforcement is currently implemented.

## Current Provider Use

- DeepSeek is the current generation provider.
- Voyage `voyage-4-large` produces document and query embeddings.
- Voyage `rerank-2.5` reranks tenant-filtered candidate text.
- Provider implementations are replaceable adapters behind platform contracts.
- Ollama is legacy only and is not target architecture.

Current retrieval code scopes candidates by tenant before reranking and sends
the query and selected chunk text rather than tenant credentials or internal
authorization objects. This is a useful control but is not a complete data
classification system.

## Required Decision Flow

```text
Input or knowledge content
  -> identify owner and tenant
  -> assign approved classification
  -> evaluate purpose, provider, region, contract, and retention policy
     -> allowed externally: send minimum necessary content
     -> restricted but transformable: redact or tokenize, then reevaluate
     -> approved-provider-only: route only to that approved provider
     -> local-provider-required: use an approved local implementation
     -> prohibited or unresolved: block and record a safe policy outcome
```

## Proposed Classification Handling

| Classification | External-provider posture |
|---|---|
| Public | May be allowed after integrity and purpose checks |
| Internal | Requires owner-approved provider policy and minimum disclosure |
| Confidential | Default restricted; approved provider and controls required |
| Restricted / regulated | Default block, redact, or approved local/provider path |

Classification labels and final definitions require management, security, and
data-owner approval. Absence of a label must not be interpreted as public.

## Data Minimization

- Send only fields needed for embedding, reranking, or generation.
- Never send API keys, JWTs, passwords, database credentials, or internal
  authorization context.
- Avoid provider transmission of tenant IDs, user identifiers, and operational
  metadata unless an approved purpose requires them.
- Reranking should receive only the query and already tenant-filtered candidate
  text.
- Logs and provider errors must not expose secrets or raw sensitive content.

## Redaction, Blocking, and Local Providers

Redaction and blocking are target controls. Before they are automated, pilot
datasets must be selected and reviewed manually under an approved policy. A
future local provider is a policy option, not an endorsement of Ollama or a
commitment to buy GPU infrastructure.

## Provider Approval Inputs

Approval must consider contractual data use, retention, training use, region,
subprocessors, encryption, incident notification, deletion, availability,
quality, latency, and cost. Approved model names and purposes should be
recorded separately from secrets.

## Current Gaps

- No automated classification or redaction gate.
- No persistent provider-policy decision attached to each request.
- No approved classification taxonomy or provider register in the repository.
- No complete provider cost/usage telemetry.
- No approved restricted-data local-provider implementation.

## Required Approval

Management approves business use; the data owner approves purpose; Security
approves classification handling and provider controls; Operations approves
secret and incident procedures. Approvers are currently TBD.
