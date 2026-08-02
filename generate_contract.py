#!/usr/bin/env python3
"""Standalone OpenAPI generator - runs without backend imports until needed."""
import subprocess
import sys

code = '''
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, ".")
os.environ.update({
    "MAAP_ENVIRONMENT": "test",
    "MAAP_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "MAAP_DEEPSEEK_API_KEY": "test-key-for-schema-generation-only",
    "MAAP_ADMIN_API_KEY": "test-admin-key-for-schema-only",
    "MAAP_JWT_SECRET_KEY": "test-jwt-secret-minimum-32-characters-long-for-openapi-gen",
    "MAAP_WIDGET_JWT_SECRET_KEY": "test-widget-jwt-secret-32-characters-long-openapi",
})

from backend.app.main import create_app
from fastapi.openapi.utils import get_openapi

app = create_app()
schema = get_openapi(
    title=app.title,
    version=app.version,
    description="Modern AI Agent Platform - Multi-tenant SaaS with RAG and embeddable widget",
    routes=app.routes,
    servers=[
        {"url": "http://localhost:8000", "description": "Local development"},
        {"url": "https://api.example.com", "description": "Production"}
    ]
)

# Add security schemes
security_schemes = {
    "AdminJWT": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Admin JWT access token from /api/v1/admin/auth/login endpoint. Grants access to administrative endpoints based on role permissions. Short-lived token (default: 15 minutes). Use refresh token endpoint to obtain new access tokens."
    },
    "InternalAdminKey": {
        "type": "apiKey",
        "in": "header",
        "name": "X-Admin-Key",
        "description": "Legacy administrative credential for backward compatibility. Grants super_admin role access to all administrative endpoints. **Deprecated:** Use AdminJWT (Bearer token) for new integrations. This scheme may be disabled in future releases."
    },
    "TenantApiKey": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "Server-side tenant API key for machine-to-machine communication. Grants access to chat and knowledge endpoints for a specific tenant. **Never expose this key in browser code.** Format: `maap_<key_id>_<secret>`"
    },
    "WidgetToken": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Short-lived widget session token for browser-based chat clients. Obtained via /api/v1/widget/bootstrap endpoint using public widget ID. Scoped to specific origin and session. Lifetime: 10 minutes (default). **Safe for browser use** - does not expose tenant secrets."
    }
}

if "components" not in schema:
    schema["components"] = {}
schema["components"]["securitySchemes"] = security_schemes

# Sort for determinism
def sort_dict(obj):
    if isinstance(obj, dict):
        return {k: sort_dict(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [sort_dict(x) for x in obj]
    return obj

schema = sort_dict(schema)

output = Path("backend/openapi.json")
output.parent.mkdir(exist_ok=True)
with open(output, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2, ensure_ascii=False, sort_keys=True)
    f.write("\\n")

print(f"✓ Generated: {output}")
print(f"  Paths: {len(schema.get('paths', {}))}")
print(f"  Components: {len(schema.get('components', {}).get('schemas', {}))}")
'''

result = subprocess.run(
    [sys.executable, "-c", code],
    capture_output=True,
    text=True,
    timeout=30
)

print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)
    
sys.exit(result.returncode)
