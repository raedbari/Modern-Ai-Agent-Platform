#!/usr/bin/env python3
"""Generate TypeScript API clients from OpenAPI schema."""

import json
from pathlib import Path

# Paths
backend_dir = Path("backend")
frontend_dir = Path("frontend")
openapi_path = backend_dir / "openapi.json"
output_dir = frontend_dir / "src" / "lib" / "api"

# Load schema
schema = json.load(open(openapi_path))

# Filter paths for each client
admin_prefixes = ["/api/admin", "/api/chat", "/api/knowledge-bases", "/health", "/ready"]
widget_prefixes = ["/api/widget", "/api/chat", "/health"]

def filter_paths(paths, prefixes):
    return {p: m for p, m in paths.items() if any(p.startswith(pre) for pre in prefixes)}

admin_paths = filter_paths(schema['paths'], admin_prefixes)
widget_paths = filter_paths(schema['paths'], widget_prefixes)

# Create output directory
output_dir.mkdir(parents=True, exist_ok=True)

# Generate Admin Client
admin_client = f'''/**
 * Admin API Client Types
 * 
 * AUTO-GENERATED from OpenAPI schema - DO NOT EDIT MANUALLY
 * To regenerate: python3 generate_ts_clients.py
 * 
 * Security: AdminJWT, InternalAdminKey, TenantApiKey
 * Usage: SERVER-SIDE ONLY - Never import in browser code
 */

export const ADMIN_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Runtime safety check
if (typeof window !== 'undefined') {{
  console.error('[SECURITY] Admin API client imported in browser! Use widget-client instead.');
}}

// ============================================================================
// API Paths
// ============================================================================

export const AdminApiPaths = {{
{chr(10).join(f'  "{path}": "{path}",' for path in sorted(admin_paths.keys()))}
}} as const;

export type AdminApiPath = keyof typeof AdminApiPaths;

// Total paths: {len(admin_paths)}
// Total operations: {sum(len([m for m in methods.keys() if m in ['get','post','put','patch','delete']]) for methods in admin_paths.values())}
'''

# Generate Widget Client  
widget_client = f'''/**
 * Widget API Client Types
 * 
 * AUTO-GENERATED from OpenAPI schema - DO NOT EDIT MANUALLY
 * To regenerate: python3 generate_ts_clients.py
 * 
 * Security: WidgetToken (browser-safe)
 * Usage: BROWSER-SAFE - Can be used in client components
 */

export const WIDGET_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============================================================================
// API Paths
// ============================================================================

export const WidgetApiPaths = {{
{chr(10).join(f'  "{path}": "{path}",' for path in sorted(widget_paths.keys()))}
}} as const;

export type WidgetApiPath = keyof typeof WidgetApiPaths;

// Total paths: {len(widget_paths)}
// Total operations: {sum(len([m for m in methods.keys() if m in ['get','post','put','patch','delete']]) for methods in widget_paths.values())}
'''

# Write files
(output_dir / "admin-client.ts").write_text(admin_client)
(output_dir / "widget-client.ts").write_text(widget_client)

# Create index
index_content = '''/**
 * API Clients
 * 
 * - admin-client: Server-side only (admin operations)
 * - widget-client: Browser-safe (public widget operations)
 */

export * from './admin-client';
export * from './widget-client';
'''

(output_dir / "index.ts").write_text(index_content)

# Create README
readme = f'''# API Clients

Auto-generated TypeScript clients from OpenAPI schema.

## Files

- `admin-client.ts` - Server-side admin API (DO NOT use in browser)
- `widget-client.ts` - Browser-safe widget API
- `index.ts` - Convenience exports

## Regeneration

```bash
python3 generate_ts_clients.py
```

## Usage

### Server-side (API routes, server components)
```typescript
import {{ AdminApiPaths }} from '@/lib/api/admin-client';

const response = await fetch(`${{AdminApiPaths["/api/admin/tenants"]}}`);
```

### Browser-side (client components)
```typescript
import {{ WidgetApiPaths }} from '@/lib/api/widget-client';

const response = await fetch(`${{WidgetApiPaths["/api/widget/bootstrap"]}}`);
```

## Statistics

- Admin paths: {len(admin_paths)}
- Widget paths: {len(widget_paths)}
- Total schemas: {len(schema.get('components', {{}}).get('schemas', {{})))}
'''

(output_dir / "README.md").write_text(readme)

print("✅ TypeScript clients generated successfully!")
print(f"   - {output_dir / 'admin-client.ts'} ({len(admin_paths)} paths)")
print(f"   - {output_dir / 'widget-client.ts'} ({len(widget_paths)} paths)")
print(f"   - {output_dir / 'index.ts'}")
print(f"   - {output_dir / 'README.md'}")
