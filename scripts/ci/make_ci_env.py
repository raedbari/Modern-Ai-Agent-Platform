#!/usr/bin/env python3

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".env.compose.ci"

examples = [
    ROOT / "backend/.env.example",
    ROOT / ".env.example",
]

def read_env(path):
    values = {}
    if not path.exists():
        return values

    for raw in path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines():

        line = raw.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        key, value = line.split("=", 1)

        values[key.strip()] = (
            value.strip()
            .strip('"')
            .strip("'")
        )

    return values


def safe_value(key, old=""):
    upper = key.upper()

    # Pydantic environment literal
    if (
        upper == "ENVIRONMENT"
        or upper.endswith("_ENVIRONMENT")
    ):
        return "test"

    # Database
    if "DATABASE_URL" in upper or upper.endswith("DB_URL"):
        return (
            "postgresql+asyncpg://"
            "maap:ci-maap-password"
            "@postgres:5432/maap"
        )

    if upper in {"POSTGRES_USER", "DB_USER"}:
        return "maap"

    if upper in {"POSTGRES_DB", "DB_NAME"}:
        return "maap"

    if upper in {
        "POSTGRES_PASSWORD",
        "DB_PASSWORD",
    }:
        return "ci-maap-password"

    # Redis
    if "REDIS" in upper and (
        "URL" in upper or "URI" in upper
    ):
        return "redis://redis:6379/0"

    # Paid providers are never real in PR CI
    if "VOYAGE_API_KEY" in upper:
        return "ci-disabled-voyage"

    if "DEEPSEEK_API_KEY" in upper:
        return "ci-disabled-deepseek"

    # Generic secrets
    if any(
        marker in upper
        for marker in (
            "SECRET",
            "PASSWORD",
            "TOKEN",
            "API_KEY",
            "PRIVATE_KEY",
            "SIGNING_KEY",
        )
    ):
        return "ci-" + ("a" * 64)

    # Preserve valid documented non-secret defaults
    bad = {
        "",
        "changeme",
        "change-me",
        "your-value",
        "your_value",
        "TODO",
    }

    if old and old not in bad and "${" not in old:
        return old

    if "PORT" in upper:
        if "REDIS" in upper:
            return "6379"
        if "POSTGRES" in upper or "DB_" in upper:
            return "5432"
        return "8000"

    if any(
        x in upper
        for x in (
            "COUNT",
            "LIMIT",
            "TOP_K",
            "CANDIDATE",
        )
    ):
        return "20"

    if any(
        x in upper
        for x in (
            "TIMEOUT",
            "TTL",
            "SECONDS",
        )
    ):
        return "30"

    if any(
        x in upper
        for x in (
            "ENABLED",
            "DEBUG",
            "ALLOW_",
        )
    ):
        return "false"

    if "URL" in upper or "URI" in upper:
        return "http://localhost"

    return "ci-placeholder"


values = {}

for example in examples:
    values.update(read_env(example))

compose = (
    ROOT / "compose.local.yaml"
).read_text(encoding="utf-8")

compose_keys = set(
    re.findall(
        r"\$\{([A-Z][A-Z0-9_]*)",
        compose,
    )
)

for key in set(values) | compose_keys:
    values[key] = safe_value(
        key,
        values.get(key, ""),
    )

# Always provide both forms.
values["ENVIRONMENT"] = "test"
values["MAAP_ENVIRONMENT"] = "test"

OUTPUT.write_text(
    "\n".join(
        f"{key}={values[key]}"
        for key in sorted(values)
    ) + "\n",
    encoding="utf-8",
)

print(f"CI_ENV_KEYS={len(values)}")
print("CI_ENVIRONMENT=test")
