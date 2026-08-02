# OpenAPI Schema Generation

## Overview

This directory contains a script to generate a deterministic OpenAPI JSON schema from the FastAPI backend without requiring PostgreSQL or Ollama connections.

## Script: `generate_openapi.py`

### Purpose

Generates a complete OpenAPI 3.x JSON schema for the Modern AI Agent Platform API that:
- Works without database or Ollama connections (uses test environment)
- Produces deterministic, byte-identical output on every run
- Includes detailed security scheme descriptions
- Sorts all JSON keys recursively for consistency
- Includes a trailing newline for proper file formatting

### Usage

```bash
cd /path/to/Modern-Ai-Agent-Platform
python3 backend/scripts/generate_openapi.py
```

### Output

The script generates `backend/openapi.json` with:
- **31 API endpoints** (paths)
- **40 schema definitions**
- **4 security schemes** with detailed descriptions

### Security Schemes

The generated schema includes comprehensive descriptions for all authentication methods:

#### 1. AdminJWT
- **Type:** HTTP Bearer (JWT)
- **Description:** Short-lived admin access token from login endpoint (15 minutes). Obtain via POST /admin/auth/login.
- **Use case:** Admin panel authentication

#### 2. InternalAdminKey
- **Type:** API Key (X-Admin-Key header)
- **Description:** Legacy X-Admin-Key header (deprecated). Use AdminJWT instead.
- **Use case:** Backward compatibility (being phased out)

#### 3. TenantApiKey
- **Type:** API Key (X-API-Key header)
- **Description:** Server-side tenant API key. Never expose it in a browser. Must be accompanied by X-Agent-ID header.
- **Use case:** Server-to-server API calls

#### 4. WidgetToken
- **Type:** HTTP Bearer (JWT)
- **Description:** Short-lived browser-safe token from bootstrap endpoint (10 minutes). Obtain via POST /widget/{public_widget_id}/bootstrap.
- **Use case:** Browser widget authentication

### How It Works

1. **Sets test environment variables** to avoid external dependencies:
   - `MAAP_ENVIRONMENT=test`
   - `MAAP_DATABASE_URL=sqlite+aiosqlite:///:memory:`
   - Mock API keys for DeepSeek, admin, JWT, and Redis

2. **Imports FastAPI app** using the standard `create_app()` factory

3. **Generates OpenAPI schema** using FastAPI's `get_openapi()` utility

4. **Enhances security schemes** with detailed descriptions for each auth method

5. **Sorts recursively** to ensure deterministic output (all dict keys sorted)

6. **Writes to file** with JSON indent=2 and trailing newline

### Determinism Verification

The script produces byte-identical output on multiple runs:

```bash
# Run twice and compare
python3 backend/scripts/generate_openapi.py
cp backend/openapi.json /tmp/run1.json
python3 backend/scripts/generate_openapi.py
diff /tmp/run1.json backend/openapi.json  # No differences

# Or use the test script
python3 backend/test_determinism.py
```

### Requirements

The script requires Python packages listed in `backend/requirements.txt`:
- fastapi
- pydantic-settings
- sqlalchemy
- pgvector
- All other backend dependencies

Install with:
```bash
pip install -r backend/requirements.txt
```

### Logging

The script creates `backend/openapi_generation.log` with detailed execution information for debugging.

## Testing Scripts

### `verify_openapi.py`

Verifies the generated OpenAPI schema structure:
- Checks for security schemes presence
- Counts paths and schemas
- Validates JSON structure
- Creates `backend/verify_openapi.log`

### `test_determinism.py`

Tests that the generation is deterministic:
- Runs the generator twice
- Compares SHA256 hashes
- Verifies byte-identical output
- Creates `backend/test_determinism.log`

## Integration

The generated `openapi.json` can be used for:
- API documentation (Swagger UI, Redoc)
- Client SDK generation (OpenAPI Generator)
- API testing and validation
- Contract testing
- API versioning and change tracking
