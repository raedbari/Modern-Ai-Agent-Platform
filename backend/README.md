# Modern AI Agent Platform — Backend

This directory contains the initial FastAPI backend foundation. It currently
provides configuration loading and a public health endpoint only.

## Requirements

- Python 3.12
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

## Run the tests

From the project root:

```powershell
python -m pytest backend\tests -v
```
