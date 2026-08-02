# OpenAPI Contract Governance Guide

## Overview

This project uses **OpenAPI Contract Governance** to ensure API stability, type safety, and prevent unintended API changes. The contract is version-controlled and automatically validated in CI.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Backend → OpenAPI Schema → TypeScript Clients       │
│                                                              │
│ backend/app/     → backend/openapi.json → frontend/src/lib/ │
│   routes/                                      api/          │
└─────────────────────────────────────────────────────────────┘
```

### Files

- **`backend/openapi.json`** - Single source of truth for API contract
- **`backend/scripts/generate_openapi.py`** - Deterministic schema generator
- **`backend/tests/test_openapi_contract.py`** - Contract validation tests
- **`frontend/src/lib/api/admin-client.ts`** - Server-side admin API types
- **`frontend/src/lib/api/widget-client.ts`** - Browser-safe widget API types
- **`generate_ts_clients.py`** - TypeScript client generator
- **`.github/workflows/openapi-contract.yml`** - CI validation

## Security Schemes

The API uses 4 distinct authentication schemes:

### 1. AdminJWT (Admin Access Token)
- **Type:** HTTP Bearer (JWT)
- **Usage:** Administrative operations
- **Lifetime:** 15 minutes
- **Obtain via:** `POST /api/admin/auth/login`
- **Safety:** Server-side only

### 2. InternalAdminKey (Legacy Admin Key)
- **Type:** API Key (X-Admin-Key header)
- **Usage:** Legacy admin operations
- **Status:** ⚠️ Deprecated - use AdminJWT
- **Safety:** Server-side only

### 3. TenantApiKey (Tenant API Key)
- **Type:** API Key (X-API-Key header)
- **Usage:** Machine-to-machine tenant operations
- **Format:** `maap_<key_id>_<secret>`
- **Safety:** ⚠️ **NEVER expose in browser** - server-side only

### 4. WidgetToken (Widget Session Token)
- **Type:** HTTP Bearer (JWT)
- **Usage:** Browser-based widget chat
- **Lifetime:** 10 minutes
- **Obtain via:** `POST /api/widget/bootstrap`
- **Safety:** ✅ Browser-safe - no secrets exposed

## Generating the Contract

### Backend: OpenAPI Schema

```bash
# Generate schema (no database/Ollama required)
python3 backend/scripts/generate_openapi.py

# Output: backend/openapi.json
```

**Requirements:**
- Python 3.11+
- FastAPI and dependencies installed

**What it does:**
1. Sets test environment variables (no real secrets needed)
2. Creates FastAPI app with all routes
3. Generates OpenAPI 3.1 schema
4. Adds detailed security scheme descriptions
5. Sorts all JSON keys for deterministic output
6. Writes `backend/openapi.json` with trailing newline

**Determinism:**
Running twice produces **byte-identical** output. Verified by SHA256 hash.

### Frontend: TypeScript Clients

```bash
# Generate typed TypeScript clients
python3 generate_ts_clients.py

# Outputs:
#   - frontend/src/lib/api/admin-client.ts
#   - frontend/src/lib/api/widget-client.ts
#   - frontend/src/lib/api/index.ts
```

**What it does:**
1. Reads `backend/openapi.json`
2. Filters paths by prefix (admin vs widget)
3. Generates TypeScript const objects with path mappings
4. Adds runtime safety checks (admin client in browser detection)

**Admin Client:**
- Includes: `/api/admin/*`, `/api/chat`, `/api/knowledge-bases/*`, `/health`, `/ready`
- **Server-side only** - throws error if imported in browser

**Widget Client:**
- Includes: `/api/widget/*`, `/api/chat`, `/health`
- **Browser-safe** - no sensitive endpoints

## Updating the Contract

### When API Changes Are Made

1. **Modify backend routes** (add/change endpoints)

2. **Regenerate OpenAPI schema:**
   ```bash
   python3 backend/scripts/generate_openapi.py
   ```

3. **Update test hash** (if schema changed):
   ```bash
   # Compute new hash
   python3 << 'EOF'
   import json, hashlib
   schema = json.load(open('backend/openapi.json'))
   schema_json = json.dumps(schema, sort_keys=True, ensure_ascii=False)
   print(hashlib.sha256(schema_json.encode()).hexdigest())
   EOF
   
   # Copy hash and update in:
   # backend/tests/test_openapi_contract.py → EXPECTED_SCHEMA_HASH
   ```

4. **Regenerate TypeScript clients:**
   ```bash
   python3 generate_ts_clients.py
   ```

5. **Run validation tests:**
   ```bash
   cd backend
   python3 -m pytest tests/test_openapi_contract.py -v
   ```

6. **Verify frontend builds:**
   ```bash
   cd frontend
   npm run typecheck
   npm run build
   ```

7. **Commit all together:**
   ```bash
   git add backend/openapi.json
   git add backend/tests/test_openapi_contract.py
   git add frontend/src/lib/api/
   git commit -m "Update API contract: <describe change>"
   ```

## Contract Validation Tests

Located in `backend/tests/test_openapi_contract.py`:

### Stability Tests
- ✅ OpenAPI file exists
- ✅ Valid JSON structure
- ✅ All operationIds unique
- ✅ OperationIds follow naming conventions
- ✅ Security schemes defined with descriptions
- ✅ No undefined $ref references
- ✅ Deterministic output (sorted keys)
- ✅ Trailing newline present

### Drift Detection Tests
- ✅ Schema hash unchanged (detects any modification)
- ✅ Minimum endpoint count (detects deletions)
- ✅ Critical endpoints exist (health, login, chat, etc.)

**Run tests:**
```bash
cd backend
python3 -m pytest tests/test_openapi_contract.py -v
```

## CI Validation

GitHub Actions workflow (`.github/workflows/openapi-contract.yml`) runs on:
- Push to `main`, `develop`, `feature/*`
- Pull requests to `main`, `develop`

**Validation steps:**
1. ✅ Generate schema (verify no errors)
2. ✅ Verify deterministic output (run twice, compare)
3. ✅ Check no uncommitted changes (schema matches repo)
4. ✅ Run contract tests (all validations pass)
5. ✅ Verify security schemes (all 4 defined with descriptions)
6. ✅ Verify operationId uniqueness (no duplicates)
7. ✅ Generate TypeScript clients
8. ✅ Verify clients up-to-date (match committed versions)
9. ✅ TypeScript type check (frontend compiles)
10. ✅ Build frontend (Next.js builds successfully)

**No secrets required** - uses test environment variables.

## Usage Examples

### Server-side (Admin API)

```typescript
// app/api/admin/tenants/route.ts
import { AdminPaths, ADMIN_API_BASE } from '@/lib/api/admin-client';

export async function GET(req: Request) {
  const response = await fetch(
    `${ADMIN_API_BASE}${AdminPaths["/api/admin/tenants"]}`,
    {
      headers: {
        'Authorization': `Bearer ${adminToken}`,
      },
    }
  );
  
  return response.json();
}
```

### Browser-side (Widget API)

```typescript
// components/widget/chat.tsx
'use client';

import { WidgetPaths, WIDGET_API_BASE } from '@/lib/api/widget-client';

export function ChatWidget() {
  const sendMessage = async (message: string) => {
    const response = await fetch(
      `${WIDGET_API_BASE}${WidgetPaths["/api/chat"]}`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${widgetToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      }
    );
    
    return response.json();
  };
  
  // ... rest of component
}
```

## Troubleshooting

### "Schema hash mismatch" in tests

**Cause:** API routes changed but schema not regenerated.

**Fix:**
```bash
python3 backend/scripts/generate_openapi.py
# Update EXPECTED_SCHEMA_HASH in tests/test_openapi_contract.py
python3 generate_ts_clients.py
git add -A && git commit -m "Update API contract"
```

### "Duplicate operationId" error

**Cause:** Two endpoints have the same `operationId`.

**Fix:** Add unique `operation_id` parameter to FastAPI route:
```python
@router.get("/path", operation_id="unique_operation_name")
def my_endpoint():
    pass
```

### "TypeScript clients have uncommitted changes" in CI

**Cause:** Schema changed but clients not regenerated.

**Fix:**
```bash
python3 generate_ts_clients.py
git add frontend/src/lib/api/
git commit -m "Regenerate TypeScript clients"
```

### "Admin client imported in browser"

**Cause:** Accidentally imported `admin-client` in a client component.

**Fix:** Use `widget-client` for browser code:
```typescript
// ❌ Wrong
import { AdminPaths } from '@/lib/api/admin-client';

// ✅ Correct
import { WidgetPaths } from '@/lib/api/widget-client';
```

## Best Practices

### DO ✅

- ✅ Regenerate schema after ANY route change
- ✅ Update schema hash in tests after intentional changes
- ✅ Regenerate TypeScript clients after schema changes
- ✅ Use `widget-client` for browser/client components
- ✅ Use `admin-client` only in server components/API routes
- ✅ Commit schema + clients together
- ✅ Run contract tests before pushing

### DON'T ❌

- ❌ Manually edit `openapi.json`
- ❌ Manually edit generated TypeScript clients
- ❌ Import `admin-client` in browser code
- ❌ Commit schema without regenerating clients
- ❌ Skip contract tests
- ❌ Force-push schema changes without review
- ❌ Expose `TenantApiKey` in browser

## File Locations

```
Modern-Ai-Agent-Platform/
├── backend/
│   ├── openapi.json                          # ← OpenAPI contract (committed)
│   ├── scripts/
│   │   └── generate_openapi.py               # ← Schema generator
│   └── tests/
│       └── test_openapi_contract.py          # ← Contract tests
├── frontend/
│   └── src/
│       └── lib/
│           └── api/
│               ├── admin-client.ts           # ← Server-side types
│               ├── widget-client.ts          # ← Browser-safe types
│               └── index.ts                  # ← Convenience exports
├── generate_ts_clients.py                    # ← TypeScript generator
├── .github/
│   └── workflows/
│       └── openapi-contract.yml              # ← CI validation
└── OPENAPI_CONTRACT_GUIDE.md                 # ← This file
```

## Support

For questions or issues:
1. Check this guide
2. Run contract tests: `pytest backend/tests/test_openapi_contract.py -v`
3. Review CI logs in GitHub Actions
4. Check git diff for uncommitted changes

## Statistics

- **API Paths:** 31 endpoints
- **Admin Paths:** 26 endpoints (server-side)
- **Widget Paths:** 3 endpoints (browser-safe)
- **Security Schemes:** 4 (AdminJWT, InternalAdminKey, TenantApiKey, WidgetToken)
- **Schema Size:** ~97 KB
- **Schema Hash:** `6eb260da4d7c72cbf3dd7e87aba9e6f67e880695c68a1b36bf658baa53cb407d`
