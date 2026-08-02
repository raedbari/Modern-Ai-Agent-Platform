#!/usr/bin/env python3
"""Verify the generated OpenAPI schema."""

import json
from pathlib import Path

def main():
    openapi_file = Path(__file__).parent / "openapi.json"
    
    with open(openapi_file) as f:
        data = json.load(f)
    
    log_file = Path(__file__).parent / "verify_openapi.log"
    with open(log_file, "w") as log:
        log.write(f"OpenAPI Schema Verification\n")
        log.write(f"=" * 50 + "\n\n")
        
        log.write(f"File: {openapi_file}\n")
        log.write(f"File size: {openapi_file.stat().st_size} bytes\n\n")
        
        log.write(f"Top-level keys: {list(data.keys())}\n\n")
        
        if 'components' in data:
            log.write(f"Components keys: {list(data['components'].keys())}\n\n")
            
            if 'securitySchemes' in data['components']:
                log.write(f"✓ Security schemes found:\n")
                for name, scheme in data['components']['securitySchemes'].items():
                    log.write(f"  - {name}: {scheme.get('type')}\n")
                    log.write(f"    Description: {scheme.get('description', 'N/A')[:80]}...\n")
            else:
                log.write(f"✗ No securitySchemes found in components\n")
        else:
            log.write(f"✗ No components section found\n")
        
        log.write(f"\nPaths count: {len(data.get('paths', {}))}\n")
        log.write(f"Schemas count: {len(data.get('components', {}).get('schemas', {}))}\n")
        
        # Check if file is deterministic (sorted)
        keys_sorted = list(data.keys()) == sorted(data.keys())
        log.write(f"\nTop-level keys sorted: {keys_sorted}\n")
        
        log.write(f"\n" + "=" * 50 + "\n")
        log.write(f"Verification complete!\n")
    
    print(f"Verification complete. Results written to: {log_file}")

if __name__ == "__main__":
    main()
