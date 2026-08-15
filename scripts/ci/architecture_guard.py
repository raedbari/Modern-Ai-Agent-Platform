#!/usr/bin/env python3

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "architecture/policy.json"

policy = json.loads(
    POLICY_PATH.read_text(encoding="utf-8")
)

provider_roots = tuple(
    policy.get("provider_implementation_roots", [])
)

import_allowlist = set(
    policy.get("legacy_provider_import_allowlist", [])
)

http_allowlist = set(
    policy.get("provider_http_allowlist", [])
)

ignored_roots = tuple(
    policy.get("ignored_architecture_roots", [])
)

provider_prefixes = tuple(
    policy.get("provider_import_prefixes", [])
)

provider_domains = tuple(
    policy.get("provider_http_domains", [])
)


def git_files():
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def ignored(path: str) -> bool:
    return any(
        path.startswith(root)
        for root in ignored_roots
    )


def provider_impl(path: str) -> bool:
    return any(
        path.startswith(root)
        for root in provider_roots
    )


def provider_imports(text: str):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    found = []

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            modules = [
                alias.name
                for alias in node.names
            ]

        elif isinstance(node, ast.ImportFrom):
            modules = [
                node.module or ""
            ]

        else:
            continue

        for module in modules:
            for prefix in provider_prefixes:
                base = prefix.rstrip(".")

                if (
                    module == base
                    or module.startswith(prefix)
                ):
                    found.append(module)

    return found


errors = []
checked = 0

for rel in git_files():

    if not rel.endswith(".py"):
        continue

    if not rel.startswith("backend/"):
        continue

    if ignored(rel):
        continue

    path = ROOT / rel

    if not path.exists():
        continue

    checked += 1

    text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    # Direct provider implementation imports are forbidden
    # outside provider implementation and explicit transitional
    # integration points.
    if (
        not provider_impl(rel)
        and rel not in import_allowlist
    ):
        imports = provider_imports(text)

        for module in imports:
            errors.append(
                f"{rel}: direct provider implementation "
                f"import '{module}' is forbidden; depend on "
                "a runtime/provider interface instead."
            )

    # Provider HTTP domains may exist only inside the provider
    # implementation itself or explicit configuration files.
    if (
        not provider_impl(rel)
        and rel not in http_allowlist
    ):
        for domain in provider_domains:
            if domain in text:
                errors.append(
                    f"{rel}: direct AI-provider HTTP domain "
                    f"'{domain}' outside provider implementation."
                )


print(f"ARCHITECTURE_FILES_CHECKED={checked}")

if errors:
    print("ARCHITECTURE_GATE=FAIL")

    for error in errors:
        print(f"ERROR: {error}")

    sys.exit(1)

print("ARCHITECTURE_GATE=PASS")
