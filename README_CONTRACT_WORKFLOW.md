# Quick Reference: OpenAPI Contract Workflow

## 🚀 Quick Commands

### Generate Everything
```bash
# From project root
./scripts/regenerate-contract.sh
```

### Individual Steps

```bash
# 1. Generate OpenAPI schema
python3 backend/scripts/generate_openapi.py

# 2. Generate TypeScript clients  
python3 generate_ts_clients.py

# 3. Run contract tests
cd backend && python3 -m pytest tests/test_openapi_contract.py -v

# 4. Type check frontend
cd frontend && npm run typecheck

# 5. Build frontend
cd frontend && npm run build
```

## 📋 Checklist: Adding/Modifying API Endpoints

- [ ] 1. Modify FastAPI route in `backend/app/api/routes/`
- [ ] 2. Run `python3 backend/scripts/generate_openapi.py`
- [ ] 3. Check diff: `git diff backend/openapi.json`
- [ ] 4. Update schema hash in `backend/tests/test_openapi_contract.py`
- [ ] 5. Run `python3 generate_ts_clients.py`
- [ ] 6. Run contract tests: `cd backend && pytest tests/test_openapi_contract.py -v`
- [ ] 7. Run frontend typecheck: `cd frontend && npm run typecheck`
- [ ] 8. Commit all together:
  ```bash
  git add backend/openapi.json backend/tests/test_openapi_contract.py frontend/src/lib/api/
  git commit -m "api: <describe change>"
  ```

## 🔐 Security Reminders

| Client | Usage | Safety |
|--------|-------|--------|
| `admin-client.ts` | Server-side admin ops | ⚠️ Server only |
| `widget-client.ts` | Browser widget ops | ✅ Browser safe |

**Never** import `admin-client` in client components!

## 🐛 Common Issues

### Schema hash mismatch
```bash
# Regenerate and update hash
python3 backend/scripts/generate_openapi.py
python3 -c "import json, hashlib; s=json.load(open('backend/openapi.json')); print(hashlib.sha256(json.dumps(s,sort_keys=True,ensure_ascii=False).encode()).hexdigest())"
# Copy hash to tests/test_openapi_contract.py → EXPECTED_SCHEMA_HASH
```

### Duplicate operationId
```python
# Add unique operation_id to route
@router.get("/path", operation_id="unique_name_here")
```

### TypeScript clients out of date
```bash
python3 generate_ts_clients.py
git add frontend/src/lib/api/
```

## 📊 Stats

- **Total Endpoints:** 31
- **Admin Paths:** 26 (server-side)
- **Widget Paths:** 3 (browser-safe)
- **Security Schemes:** 4

See `OPENAPI_CONTRACT_GUIDE.md` for full documentation.
