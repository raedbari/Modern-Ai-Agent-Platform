#!/usr/bin/env python3
"""Generate the canonical deterministic OpenAPI contract.

The generator runs without PostgreSQL, Redis, Ollama, or production secrets.
It writes only the requested JSON file and creates no logs or temporary
artifacts inside the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "backend" / "openapi.json"

SAFE_GENERATION_ENVIRONMENT = {
    "MAAP_ENVIRONMENT": "test",
    "MAAP_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "MAAP_DEEPSEEK_API_KEY": "openapi-generation-placeholder",
    "MAAP_ADMIN_API_KEY": "openapi-generation-placeholder",
    "MAAP_JWT_SECRET_KEY": (
        "openapi-generation-placeholder-at-least-32-characters"
    ),
    "MAAP_WIDGET_JWT_SECRET_KEY": (
        "widget-openapi-placeholder-at-least-32-characters"
    ),
    "MAAP_REDIS_URL": "redis://localhost:6379/0",
}


def configure_generation_environment() -> None:
    """Force a safe environment before importing the application."""

    for name, value in SAFE_GENERATION_ENVIRONMENT.items():
        os.environ[name] = value

    repository_path = str(REPOSITORY_ROOT)

    if repository_path not in sys.path:
        sys.path.insert(0, repository_path)


def normalize_schema(obj: Any) -> Any:
    """Ensure deterministic schema ordering across Python and Pydantic versions."""
    if isinstance(obj, dict):
        normalized = {}
        for key in sorted(obj.keys()):
            val = obj[key]
            if key == "anyOf" and isinstance(val, list):
                sorted_items = sorted(
                    [normalize_schema(item) for item in val],
                    key=lambda x: json.dumps(x, sort_keys=True),
                )
                normalized[key] = sorted_items
            else:
                normalized[key] = normalize_schema(val)
        return normalized
    elif isinstance(obj, list):
        return [normalize_schema(item) for item in obj]
    return obj


def build_openapi_schema() -> dict[str, Any]:
    """Build the contract from the current FastAPI application."""

    configure_generation_environment()

    from backend.app.main import create_app

    app = create_app()

    # Avoid reusing a schema cached by any application customization.
    app.openapi_schema = None

    schema = app.openapi()

    if not isinstance(schema, dict):
        raise TypeError("FastAPI returned a non-object OpenAPI schema.")

    return normalize_schema(schema)


def serialize_openapi_schema(
    schema: dict[str, Any],
) -> str:
    """Serialize with stable key ordering and one trailing newline."""

    return (
        json.dumps(
            schema,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )


def write_openapi_schema(output_path: Path) -> dict[str, Any]:
    """Generate and atomically write the canonical contract."""

    schema = build_openapi_schema()
    content = serialize_openapi_schema(schema)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    temporary_path.write_text(
        content,
        encoding="utf-8",
        newline="\n",
    )

    temporary_path.replace(output_path)

    return schema


def operation_count(
    schema: dict[str, Any],
) -> int:
    """Count HTTP operations in an OpenAPI schema."""

    methods = {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "options",
        "head",
        "trace",
    }

    return sum(
        1
        for path_item in schema.get("paths", {}).values()
        if isinstance(path_item, dict)
        for method in path_item
        if method.lower() in methods
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate backend/openapi.json deterministically.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSON path.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    output_path = args.output.resolve()
    schema = write_openapi_schema(output_path)

    paths = schema.get("paths", {})
    security_schemes = (
        schema.get("components", {})
        .get("securitySchemes", {})
    )

    print(f"OPENAPI_OUTPUT={output_path}")
    print(f"OPENAPI_VERSION={schema.get('openapi')}")
    print(f"PATH_COUNT={len(paths)}")
    print(f"OPERATION_COUNT={operation_count(schema)}")
    print(
        "SECURITY_SCHEMES="
        + ",".join(sorted(security_schemes))
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
