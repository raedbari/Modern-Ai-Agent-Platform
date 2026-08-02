#!/usr/bin/env python3
"""Run OpenAPI contract tests and save results."""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_openapi_contract.py", "-v"],
    capture_output=True,
    text=True,
    timeout=30
)

print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)

# Save to file
with open("contract_test_results.txt", "w") as f:
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)

sys.exit(result.returncode)
