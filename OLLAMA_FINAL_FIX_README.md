# MAAP Ollama CPU reliability fix

This package is intended to be extracted into the root of the
`Ai-Agent-Platform` repository.

## What the fix changes

- Sends `num_ctx=1024` and `num_batch=64` on every Ollama embedding request.
- Keeps the application-level chunk batch at 8 texts per request.
- Forces Ollama to use `cpu_avx2` because CUDA/PTX JIT crashes on the target
  Windows/RTX 2060 installation.
- Retries transient Ollama/network failures twice with bounded backoff.
- Does not expose Ollama response bodies, model paths, or stack details.
- Uses the durable `document-jobs` upload path in the E2E test.
- Keeps a document `pending` while its durable job is waiting to retry.
- Marks a document `failed` only after the final job attempt is exhausted.
- Adds a Windows startup probe so Docker is not started when embeddings fail.

## Apply and run on Windows

Extract the ZIP into the repository root and allow it to replace the included
files. Then run these commands in Windows PowerShell from the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\configure-ollama.ps1
.\scripts\local-up.ps1 -Build
.\maap_two_tenant_e2e.ps1
```

The first script persists these Ollama server settings for the current Windows
user and restarts Ollama:

```text
OLLAMA_LLM_LIBRARY=cpu_avx2
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_NUM_PARALLEL=1
```

It then runs a real `qwen3-embedding:0.6b` request with the same bounded
options used by the backend. The command must finish with:

```text
Ollama configuration and embedding probe succeeded.
```

`ollama ps` should show the embedding model on the CPU and context `1024`.

## Expected API behavior

- Customer-facing upload uses `POST /document-jobs` and returns HTTP `202`.
- Temporary Ollama failures are retried by both the provider and durable job.
- Chat returns HTTP `200` with `answer_status=temporarily_unavailable` if
  verified retrieval is temporarily unavailable.
- A permanently failed ingestion job is visible as job/document state; raw
  Ollama errors are never returned to the customer.

## Verification already completed

The complete backend suite passed after the change:

```text
402 passed
```

The real CPU/Ollama probe and Docker E2E run must still be completed on the
target Windows machine because those services are not available in the build
workspace.
