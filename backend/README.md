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
