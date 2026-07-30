# Modern AI Agent Platform — Backend

This directory contains the FastAPI backend for authenticated multi-tenant
chat and the knowledge RAG pipeline. It includes SQLAlchemy persistence,
Alembic migrations, document parsing/chunking/embedding, and tenant- and
agent-scoped vector retrieval.

## Requirements

- Python 3.12
- PostgreSQL with the `vector` extension available
- Run commands from the project root

## Windows setup

Create and activate a virtual environment if the project does not already have
one:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```powershell
python -m pip install -r backend\requirements.txt
```

## Environment variables

For local overrides, copy the example file:

```powershell
Copy-Item backend\.env.example backend\.env
```

Settings use the `MAAP_` prefix and are loaded from operating-system
environment variables or `backend/.env`. Do not commit `backend/.env`.

## Database migrations

Apply the schema before starting the API:

```powershell
python -m alembic -c backend\alembic.ini upgrade head
```

The knowledge migration enables `vector`, creates a `VECTOR(1024)` embedding
column, and adds an HNSW cosine index. The configured database role therefore
needs permission to create the extension. If production policy disallows
that permission, a database administrator must run this once:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Run the API

From the project root:

```powershell
python -m uvicorn backend.app.main:app --reload
```

Open `http://127.0.0.1:8000/health`. The endpoint returns:

```json
{
  "status": "ok",
  "service": "Modern AI Agent Platform API",
  "environment": "development"
}
```

Interactive API documentation is available at
`http://127.0.0.1:8000/docs`.

## Reproducible local stack on Windows

The repository includes a local-first Compose stack that keeps PostgreSQL
private, applies Alembic migrations before the API starts, and connects the API
container to Ollama running on Windows through `host.docker.internal`.

Prerequisites:

- Docker Desktop is running.
- Ollama is running on `127.0.0.1:11434`.
- `qwen3-embedding:0.6b` is installed.

Start the stack from PowerShell:

```powershell
.\scripts\local-up.ps1 -Build
```

The script creates a Git-ignored `.env.compose` with a random database
password when one does not exist. It also copies `backend/.env.example` to the
Git-ignored `backend/.env` on first use. Add the real
`MAAP_DEEPSEEK_API_KEY` to `backend/.env` before testing live generation.

Create the first tenant, agent, and server-side API key:

```powershell
docker compose --env-file .env.compose -f compose.local.yaml exec api `
  python -m backend.app.cli.bootstrap_customer `
  --tenant-id tenant-demo `
  --tenant-name "Demo Tenant" `
  --agent-id agent-demo `
  --agent-name "Demo Agent" `
  --system-prompt "Answer only from verified platform knowledge."
```

The raw API key is shown once. Store it securely. It is a server-side
credential and must not be embedded in browser JavaScript.

Inspect service state:

```powershell
docker compose --env-file .env.compose -f compose.local.yaml ps
Invoke-RestMethod http://127.0.0.1:8000/ready
```

Stop containers without deleting PostgreSQL data:

```powershell
docker compose --env-file .env.compose -f compose.local.yaml down
```

## Knowledge API

All knowledge routes require the same trusted headers as chat:

```text
X-API-Key: maap_<key-id>.<secret>
X-Agent-ID: <active-agent-id>
```

The API never accepts `tenant_id` or `agent_id` from request bodies. A newly
created knowledge base is assigned to the selected agent automatically.

Available operations:

- `POST /api/knowledge-bases`
- `GET /api/knowledge-bases`
- `GET|PATCH|DELETE /api/knowledge-bases/{knowledge_base_id}`
- `POST|GET /api/knowledge-bases/{knowledge_base_id}/documents`
- `GET|DELETE /api/knowledge-bases/{knowledge_base_id}/documents/{document_id}`
- `POST /api/knowledge-bases/{knowledge_base_id}/documents/{document_id}/reindex`

Document upload and reindex requests use `multipart/form-data` with a required
`file` field and an optional `source_name`. Reindexing requires the source file
again because raw uploads are not retained after parsing.

## Run the tests

From the project root:

```powershell
python -m pytest backend\tests -v
```
