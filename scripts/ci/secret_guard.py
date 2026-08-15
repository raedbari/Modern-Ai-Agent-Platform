#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from changed_files import changed_files

ROOT = Path(__file__).resolve().parents[2]
POLICY = json.loads((ROOT / "architecture/policy.json").read_text(encoding="utf-8"))

protected = set(POLICY["protected_secret_files"])
allowed_examples = set(POLICY["allowed_secret_examples"])

patterns = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("GitHub classic token", re.compile(r"\bghp_[A-Za-z0-9]{30,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
]

violations: list[str] = []

tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
for relative in tracked:
    name = Path(relative).name
    if relative in allowed_examples or name == ".env.example":
        continue
    if name in protected or (name.startswith(".env.") and not name.endswith(".example")):
        violations.append(f"{relative}: sensitive environment/credential file must not be tracked.")

for relative in changed_files():
    path = ROOT / relative
    if not path.is_file() or path.stat().st_size > 2_000_000:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue

    for label, pattern in patterns:
        if pattern.search(text):
            violations.append(f"{relative}: possible {label} detected.")

if violations:
    print("SECRET_GATE=FAIL")
    for violation in violations:
        print(f"::error::{violation}")
    raise SystemExit(1)

print("SECRET_GATE=PASS")
