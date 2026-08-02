#!/usr/bin/env python3
"""Simple OpenAPI generator."""
import sys
import os
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set test environment
os.environ["MAAP_ENVIRONMENT"] = "test"
os.environ["MAAP_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["MAAP_DEEPSEEK_API_KEY"] = "test-key"
os.environ["MAAP_ADMIN_API_KEY"] = "test-admin"
os.environ["MAAP_JWT_SECRET_KEY"] = "test-jwt-secret-minimum-32-chars-long-123456789"
os.environ["MAAP_WIDGET_JWT_SECRET_KEY"] = "test-widget-secret-32-chars-12345678"

from backend.app.main import create_app
from fastapi.openapi.utils import get_openapi

app = create_app()
schema = get_openapi(
    title=app.title,
    version=app.version,
    routes=app.routes
)

output_path = Path(__file__).parent.parent / "openapi.json"
with open(output_path, 'w') as f:
    json.dump(schema, f, indent=2, sort_keys=True)
    f.write('\n')

print(f"Generated: {output_path}")
print(f"Paths: {len(schema.get('paths', {}))}")
