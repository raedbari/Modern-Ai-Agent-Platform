#!/usr/bin/env python3
"""Generate deterministic OpenAPI JSON schema without requiring PostgreSQL or Ollama."""

import json
import os
import sys
import traceback
from pathlib import Path

# Add backend parent directory to path so we can import backend.app
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir.parent))


def sort_recursively(obj):
    """Recursively sort all dictionary keys for deterministic output."""
    if isinstance(obj, dict):
        return {k: sort_recursively(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [sort_recursively(item) for item in obj]
    else:
        return obj


def enhance_security_schemes(schema):
    """Add detailed security scheme descriptions."""
    security_schemes = {
        "AdminJWT": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Short-lived admin access token from login endpoint (15 minutes). Obtain via POST /admin/auth/login.",
        },
        "InternalAdminKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Admin-Key",
            "description": "Legacy X-Admin-Key header (deprecated). Use AdminJWT instead.",
        },
        "TenantApiKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Server-side tenant API key. Never expose it in a browser. Must be accompanied by X-Agent-ID header.",
        },
        "WidgetToken": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Short-lived browser-safe token from bootstrap endpoint (10 minutes). Obtain via POST /widget/{public_widget_id}/bootstrap.",
        },
    }
    
    if "components" not in schema:
        schema["components"] = {}
    schema["components"]["securitySchemes"] = security_schemes


def main():
    """Generate OpenAPI JSON schema with test environment configuration."""
    
    try:
        # Set test environment variables to avoid PostgreSQL/Ollama dependencies
        os.environ.update({
            "MAAP_ENVIRONMENT": "test",
            "MAAP_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "MAAP_DEEPSEEK_API_KEY": "test-key-placeholder",
            "MAAP_ADMIN_API_KEY": "test-admin-key-placeholder",
            "MAAP_JWT_SECRET_KEY": "test-jwt-secret-key-placeholder-32chars-minimum",
            "MAAP_WIDGET_JWT_SECRET_KEY": "test-widget-jwt-secret-key-placeholder-32chars",
            "MAAP_REDIS_URL": "redis://localhost:6379/0",
        })
        
        # Write to log file for debugging
        log_file = backend_dir / "openapi_generation.log"
        with open(log_file, "w") as log:
            log.write("Starting OpenAPI generation...\n")
            log.write(f"Backend dir: {backend_dir}\n")
            log.write(f"Python path: {sys.path}\n\n")
            
            try:
                # Import and create the FastAPI app
                log.write("Importing backend.app.main...\n")
                from backend.app.main import create_app
                from fastapi.openapi.utils import get_openapi
                log.write("Imports successful\n")
                
                log.write("Creating app...\n")
                app = create_app()
                log.write(f"App created: {app.title}\n")
                
                # Generate OpenAPI schema
                log.write("Generating OpenAPI schema...\n")
                schema = get_openapi(
                    title=app.title,
                    version=app.version,
                    openapi_version=app.openapi_version,
                    description=app.description,
                    routes=app.routes,
                )
                log.write(f"Schema generated with {len(schema.get('paths', {}))} paths\n")
                
                # Enhance with detailed security scheme descriptions
                log.write("Enhancing security schemes...\n")
                enhance_security_schemes(schema)
                
                # Sort all keys recursively for deterministic output
                log.write("Sorting schema recursively...\n")
                schema = sort_recursively(schema)
                
                # Write to backend/openapi.json with trailing newline
                output_path = backend_dir / "openapi.json"
                log.write(f"Writing to {output_path}...\n")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(schema, f, indent=2, ensure_ascii=False)
                    f.write("\n")  # Ensure trailing newline
                
                log.write("SUCCESS!\n")
                
                # Print to stdout
                print(f"✓ OpenAPI schema generated: {output_path}")
                print(f"  Title: {schema['info']['title']}")
                print(f"  Version: {schema['info']['version']}")
                print(f"  Paths: {len(schema.get('paths', {}))}")
                print(f"  Security Schemes: {len(schema.get('components', {}).get('securitySchemes', {}))}")
                
            except Exception as e:
                log.write(f"\nERROR: {e}\n")
                log.write(traceback.format_exc())
                raise
                
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
