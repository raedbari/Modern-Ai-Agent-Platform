#!/usr/bin/env python3
"""Test that the OpenAPI generation is deterministic."""

import hashlib
import subprocess
import sys
from pathlib import Path

def get_file_hash(filepath):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def main():
    backend_dir = Path(__file__).parent
    script_path = backend_dir / "scripts" / "generate_openapi.py"
    output_path = backend_dir / "openapi.json"
    
    log_file = backend_dir / "test_determinism.log"
    with open(log_file, "w") as log:
        log.write("Testing OpenAPI generation determinism\n")
        log.write("=" * 80 + "\n\n")
        
        # First run
        log.write("Running generation script (first time)...\n")
        result1 = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=backend_dir.parent,
            capture_output=True,
            text=True
        )
        if result1.returncode != 0:
            log.write(f"ERROR: First run failed\n")
            log.write(f"STDOUT: {result1.stdout}\n")
            log.write(f"STDERR: {result1.stderr}\n")
            print(f"First run failed. See {log_file}")
            return False
        
        if not output_path.exists():
            log.write(f"ERROR: Output file not created: {output_path}\n")
            print(f"Output file not created. See {log_file}")
            return False
        
        hash1 = get_file_hash(output_path)
        size1 = output_path.stat().st_size
        log.write(f"✓ First run completed\n")
        log.write(f"  File size: {size1} bytes\n")
        log.write(f"  SHA256: {hash1}\n\n")
        
        # Second run
        log.write("Running generation script (second time)...\n")
        result2 = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=backend_dir.parent,
            capture_output=True,
            text=True
        )
        if result2.returncode != 0:
            log.write(f"ERROR: Second run failed\n")
            log.write(f"STDOUT: {result2.stdout}\n")
            log.write(f"STDERR: {result2.stderr}\n")
            print(f"Second run failed. See {log_file}")
            return False
        
        hash2 = get_file_hash(output_path)
        size2 = output_path.stat().st_size
        log.write(f"✓ Second run completed\n")
        log.write(f"  File size: {size2} bytes\n")
        log.write(f"  SHA256: {hash2}\n\n")
        
        # Compare
        log.write("=" * 80 + "\n")
        if hash1 == hash2 and size1 == size2:
            log.write("✓ SUCCESS: Output is deterministic (byte-identical)\n")
            log.write(f"  Both runs produced identical files\n")
            log.write(f"  SHA256: {hash1}\n")
            print(f"✓ Determinism test PASSED")
            print(f"  Both runs produced byte-identical output")
            print(f"  SHA256: {hash1}")
            return True
        else:
            log.write("✗ FAILURE: Output differs between runs\n")
            log.write(f"  First run:  {hash1} ({size1} bytes)\n")
            log.write(f"  Second run: {hash2} ({size2} bytes)\n")
            print(f"✗ Determinism test FAILED")
            print(f"  Output differs between runs")
            return False
    
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
