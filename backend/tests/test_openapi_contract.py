"""Governance tests for the committed OpenAPI contract."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent

OPENAPI_PATH = BACKEND_ROOT / "openapi.json"
GENERATOR_PATH = (
    BACKEND_ROOT
    / "scripts"
    / "generate_openapi.py"
)

HTTP_METHODS = {
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "options",
    "head",
    "trace",
}

REQUIRED_SECURITY_SCHEMES = {
    "AdminJWT",
    "InternalAdminKey",
    "TenantApiKey",
    "WidgetToken",
}

CRITICAL_OPERATIONS = {
    ("get", "/health"),
    ("get", "/ready"),
    ("post", "/api/admin/auth/login"),
    (
        "patch",
        (
            "/api/admin/tenants/{tenant_id}"
            "/agents/{agent_id}/config"
        ),
    ),
    ("post", "/api/widget/bootstrap"),
    ("post", "/api/chat"),
    (
        "post",
        (
            "/api/knowledge-bases/{knowledge_base_id}"
            "/documents"
        ),
    ),
    (
        "post",
        (
            "/api/knowledge-bases/{knowledge_base_id}"
            "/documents/{document_id}/reindex"
        ),
    ),
}


def load_committed_schema() -> dict[str, Any]:
    assert OPENAPI_PATH.exists(), (
        "backend/openapi.json is missing. Run "
        "`python backend/scripts/generate_openapi.py`."
    )

    loaded = json.loads(
        OPENAPI_PATH.read_text(encoding="utf-8")
    )

    assert isinstance(loaded, dict)

    return loaded


def iter_operations(
    schema: dict[str, Any],
):
    for path, path_item in schema.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue

        for method, operation in path_item.items():
            normalized_method = method.lower()

            if normalized_method not in HTTP_METHODS:
                continue

            assert isinstance(operation, dict)

            yield normalized_method, path, operation


def generate_to(output_path: Path) -> bytes:
    result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR_PATH),
            "--output",
            str(output_path),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        "OpenAPI generation failed.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    assert output_path.exists()

    return output_path.read_bytes()


def resolve_local_reference(
    schema: dict[str, Any],
    reference: str,
) -> bool:
    if not reference.startswith("#/"):
        return False

    current: Any = schema

    for raw_token in reference[2:].split("/"):
        token = (
            raw_token
            .replace("~1", "/")
            .replace("~0", "~")
        )

        if not isinstance(current, dict):
            return False

        if token not in current:
            return False

        current = current[token]

    return True


def collect_references(
    value: Any,
    output: set[str],
) -> None:
    if isinstance(value, dict):
        reference = value.get("$ref")

        if isinstance(reference, str):
            output.add(reference)

        for nested in value.values():
            collect_references(nested, output)

    elif isinstance(value, list):
        for nested in value:
            collect_references(nested, output)


def test_committed_contract_matches_current_application(
    tmp_path: Path,
) -> None:
    generated = generate_to(
        tmp_path / "openapi.json"
    )

    assert generated == OPENAPI_PATH.read_bytes(), (
        "backend/openapi.json has drifted from the current FastAPI "
        "application. Regenerate and review the contract."
    )


def test_generation_is_byte_deterministic(
    tmp_path: Path,
) -> None:
    first = generate_to(
        tmp_path / "first.json"
    )

    second = generate_to(
        tmp_path / "second.json"
    )

    assert first == second


def test_contract_is_canonical_json() -> None:
    raw = OPENAPI_PATH.read_text(encoding="utf-8")
    schema = json.loads(raw)

    expected = (
        json.dumps(
            schema,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )

    assert raw == expected
    assert raw.endswith("\n")
    assert not raw.endswith("\n\n")


def test_openapi_structure_and_size() -> None:
    schema = load_committed_schema()

    assert schema["openapi"].startswith("3.")
    assert isinstance(schema.get("info"), dict)
    assert isinstance(schema.get("paths"), dict)
    assert isinstance(schema.get("components"), dict)

    operations = list(iter_operations(schema))

    assert len(schema["paths"]) >= 30
    assert len(operations) >= 35


def test_operation_ids_are_present_unique_and_stable() -> None:
    schema = load_committed_schema()

    operation_ids = []

    for method, path, operation in iter_operations(schema):
        operation_id = operation.get("operationId")

        assert isinstance(operation_id, str), (
            f"Missing operationId for {method.upper()} {path}"
        )

        assert re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            operation_id,
        ), (
            f"Unstable operationId for "
            f"{method.upper()} {path}: {operation_id!r}"
        )

        operation_ids.append(operation_id)

    duplicates = {
        operation_id: count
        for operation_id, count
        in Counter(operation_ids).items()
        if count > 1
    }

    assert duplicates == {}


def test_critical_operations_exist() -> None:
    schema = load_committed_schema()

    available = {
        (method, path)
        for method, path, _ in iter_operations(schema)
    }

    missing = CRITICAL_OPERATIONS - available

    assert missing == set()


def test_required_security_schemes_are_defined() -> None:
    schema = load_committed_schema()

    schemes = (
        schema.get("components", {})
        .get("securitySchemes", {})
    )

    assert REQUIRED_SECURITY_SCHEMES <= set(schemes)

    assert schemes["AdminJWT"]["type"] == "http"
    assert schemes["AdminJWT"]["scheme"] == "bearer"

    assert schemes["InternalAdminKey"]["type"] == "apiKey"
    assert schemes["InternalAdminKey"]["in"] == "header"
    assert schemes["InternalAdminKey"]["name"] == "X-Admin-Key"

    assert schemes["TenantApiKey"]["type"] == "apiKey"
    assert schemes["TenantApiKey"]["in"] == "header"
    assert schemes["TenantApiKey"]["name"] == "X-API-Key"

    assert schemes["WidgetToken"]["type"] == "http"
    assert schemes["WidgetToken"]["scheme"] == "bearer"


def test_operation_security_references_are_defined() -> None:
    schema = load_committed_schema()

    schemes = set(
        schema.get("components", {})
        .get("securitySchemes", {})
    )

    undefined: list[str] = []

    for method, path, operation in iter_operations(schema):
        for requirement in operation.get("security", []):
            if not isinstance(requirement, dict):
                continue

            for scheme_name in requirement:
                if scheme_name not in schemes:
                    undefined.append(
                        f"{method.upper()} {path}: {scheme_name}"
                    )

    assert undefined == []


def test_all_local_references_are_defined() -> None:
    schema = load_committed_schema()

    references: set[str] = set()
    collect_references(schema, references)

    external = sorted(
        reference
        for reference in references
        if not reference.startswith("#/")
    )

    undefined = sorted(
        reference
        for reference in references
        if reference.startswith("#/")
        and not resolve_local_reference(schema, reference)
    )

    assert external == []
    assert undefined == []


def test_contract_does_not_contain_generation_secrets() -> None:
    raw = OPENAPI_PATH.read_text(encoding="utf-8")

    forbidden = {
        "openapi-generation-placeholder",
        "widget-openapi-placeholder",
        "test-admin-key",
        "test-jwt-secret",
    }

    exposed = sorted(
        value
        for value in forbidden
        if value in raw
    )

    assert exposed == []


@pytest.mark.parametrize(
    ("method", "path"),
    sorted(CRITICAL_OPERATIONS),
)
def test_critical_operation_has_operation_id(
    method: str,
    path: str,
) -> None:
    schema = load_committed_schema()

    operation = schema["paths"][path][method]

    assert operation.get("operationId")

def test_operation_security_contract() -> None:
    """Protect public and authenticated endpoint security semantics."""

    schema = load_committed_schema()
    paths = schema["paths"]

    def security(
        method: str,
        path: str,
    ) -> list[dict[str, list[str]]] | None:
        return paths[path][method].get("security")

    # Public token-issuing endpoints must remain public.
    assert security(
        "post",
        "/api/admin/auth/login",
    ) is None

    assert security(
        "post",
        "/api/admin/auth/refresh",
    ) is None

    assert security(
        "post",
        "/api/widget/bootstrap",
    ) is None

    # JWT-only administrative session endpoints.
    assert security(
        "post",
        "/api/admin/auth/logout",
    ) == [
        {"AdminJWT": []},
    ]

    assert security(
        "get",
        "/api/admin/auth/me",
    ) == [
        {"AdminJWT": []},
    ]

    assert security(
        "post",
        "/api/admin/auth/change-password",
    ) == [
        {"AdminJWT": []},
    ]

    agent_config_path = (
        "/api/admin/tenants/{tenant_id}"
        "/agents/{agent_id}/config"
    )

    # Separate objects mean logical OR in OpenAPI.
    assert security(
        "patch",
        agent_config_path,
    ) == [
        {"InternalAdminKey": []},
        {"AdminJWT": []},
    ]

    assert security(
        "post",
        "/api/chat",
    ) == [
        {"TenantApiKey": []},
        {"WidgetToken": []},
        {"TenantUserJWT": []},
    ]
