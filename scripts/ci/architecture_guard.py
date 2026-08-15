#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from changed_files import changed_files

ROOT = Path(__file__).resolve().parents[2]
POLICY = json.loads((ROOT / "architecture/policy.json").read_text(encoding="utf-8"))

provider_roots = tuple(POLICY["provider_implementation_roots"])
legacy_allow = set(POLICY["legacy_provider_import_allowlist"])
provider_prefixes = POLICY["provider_import_prefixes"]
provider_domains = POLICY["provider_http_domains"]

violations: list[str] = []
checked = 0

for relative in changed_files():
    path = ROOT / relative
    if not path.is_file():
        continue
    if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx"}:
        continue

    checked += 1
    text = path.read_text(encoding="utf-8", errors="ignore")

    if relative not in legacy_allow and not relative.startswith(provider_roots):
        for prefix in provider_prefixes:
            if prefix in text:
                violations.append(
                    f"{relative}: direct provider implementation import '{prefix}' is forbidden; "
                    "depend on a runtime/provider interface instead."
                )

    if not relative.startswith(provider_roots):
        for domain in provider_domains:
            if domain in text:
                violations.append(
                    f"{relative}: direct AI-provider HTTP domain '{domain}' outside provider implementation."
                )

    if relative.startswith("frontend/") and re.search(
        r"(DeepSeekProvider|VoyageEmbeddingProvider|VoyageRerankProvider)",
        text,
    ):
        violations.append(
            f"{relative}: frontend/product code references an AI provider implementation directly."
        )

print(f"ARCHITECTURE_FILES_CHECKED={checked}")

if violations:
    print("ARCHITECTURE_GATE=FAIL")
    for violation in violations:
        print(f"::error::{violation}")
    raise SystemExit(1)

print("ARCHITECTURE_GATE=PASS")
