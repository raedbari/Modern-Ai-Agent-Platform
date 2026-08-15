#!/usr/bin/env python3
from __future__ import annotations
import os
import subprocess

def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()

def base_sha() -> str:
    explicit = os.getenv("CI_BASE_SHA", "").strip()
    if explicit:
        return explicit
    try:
        return run("git", "merge-base", "HEAD", "origin/main")
    except Exception:
        try:
            return run("git", "rev-parse", "HEAD^")
        except Exception:
            return run("git", "rev-parse", "HEAD")

def changed_files() -> list[str]:
    base = base_sha()
    output = run("git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD")
    return [line.strip() for line in output.splitlines() if line.strip()]

if __name__ == "__main__":
    for item in changed_files():
        print(item)
