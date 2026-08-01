# Admin Authentication & RBAC - Quick Start Guide

## 🚀 What's New?

The platform now features a production-grade admin authentication system with:
- **JWT-based authentication** with access & refresh tokens
- **Role-Based Access Control (RBAC)** with 3 roles and 13 permissions
- **Argon2id password hashing** following OWASP standards
- **Refresh token rotation** with replay detection
- **Comprehensive audit logging** of all operations
- **CLI bootstrap tool** for initial setup

---

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL or SQLite database
- Alembic migrations applied
- Environment variables configured

---

## ⚡ Quick Setup (5 minutes)

### Step 1: Configure Environment

Add to your `.env` file:

```bash
# JWT Configuration (REQUIRED)
MAAP_JWT_SECRET_KEY=your-secure-random-string-at-least-32-characters-long

# Token Lifetimes (Optional - defaults shown)
MAAP_JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
MAAP_JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Legacy Key Compatibility (Disable in production!)
MAAP_ADMIN_LEGACY_KEY_ENABLED=false

# Argon2 Settings (Optional - OWASP compliant defaults)
MAAP_ARGON2_TIME_COST=2
MAAP_ARGON2_MEMORY_COST=19456
MAAP_ARGON2_PARALLELISM=1
```

### Step 2: Apply Database Migrations

```bash
cd backend
alembic upgrade head
```

This creates 3 new tables:
- `admin_users` - Admin accounts
- `admin_refresh_sessions` - Active sessions
- `admin_audit_log` - Audit trail

### Step 3: Create First Super Admin

```bash
python -m backend.app.cli.bootstrap_admin \
  --username superadmin \
  --password "YourSecurePassword123!"
```


### Step 4: Test the Setup

```bash
# Login to get tokens
curl -X POST http://localhost:8000/api/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "superadmin",
    "password": "YourSecurePassword123!"
  }'

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "maap_adm_...",
  "token_type": "Bearer",
  "expires_in": 900,
  "admin_id": "uuid",
  "role": "super_admin"
}
```

---

## 🔑 Using the API

### Authentication Header

All admin endpoints now require JWT authentication:

```bash
Authorization: Bearer <your_access_token>
```

### Example: List Tenants

```bash
curl http://localhost:8000/api/admin/tenants \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Refresh Your Token

Access tokens expire after 15 minutes. Use the refresh token to get a new one:

```bash
curl -X POST http://localhost:8000/api/admin/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "maap_adm_..."}'
```

### Logout

```bash
curl -X POST http://localhost:8000/api/admin/auth/logout \
  -H "Authorization: Bearer <your_access_token>"
```

---

## 👥 Managing Admin Users

### Create New Admin (super_admin only)

```bash
curl -X POST http://localhost:8000/api/admin/admins \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator1",
    "password": "SecurePassword456!",
    "role": "operator"
  }'
```

### List All Admins (super_admin only)

```bash
curl http://localhost:8000/api/admin/admins \
  -H "Authorization: Bearer <super_admin_token>"
```

### Deactivate Admin (super_admin only)

```bash
curl -X PATCH http://localhost:8000/api/admin/admins/{admin_id}/status \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

### Revoke All Sessions (super_admin only)

```bash
curl -X DELETE http://localhost:8000/api/admin/admins/{admin_id}/sessions \
  -H "Authorization: Bearer <super_admin_token>"
```

---

## 🛡️ Roles & Permissions

### Super Admin
- **All permissions**
- Can manage other admins
- Can perform hard deletes

### Operator
- Read/write for tenants, agents, API keys
- Cannot delete permanently
- Cannot manage admins

### Auditor
- Read-only access to all data
- Can view audit logs
- Cannot modify anything

### Permission Matrix

| Permission | super_admin | operator | auditor |
|------------|-------------|----------|---------|
| tenants:read | ✅ | ✅ | ✅ |
| tenants:write | ✅ | ✅ | ❌ |
| tenants:delete | ✅ | ❌ | ❌ |
| agents:read | ✅ | ✅ | ✅ |
| agents:write | ✅ | ✅ | ❌ |
| agents:delete | ✅ | ❌ | ❌ |
| api_keys:read | ✅ | ✅ | ✅ |
| api_keys:revoke | ✅ | ✅ | ❌ |
| conversations:delete | ✅ | ✅ | ❌ |
| admins:read | ✅ | ❌ | ❌ |
| admins:write | ✅ | ❌ | ❌ |
| admins:delete | ✅ | ❌ | ❌ |
| audit:read | ✅ | ❌ | ✅ |

---

## 🔐 Password Requirements

All passwords must meet these criteria:
- ✅ At least 12 characters
- ✅ At least 1 uppercase letter
- ✅ At least 1 digit
- ✅ At least 1 special character

Examples:
- ✅ `SecurePassword123!`
- ✅ `MyP@ssw0rd2024`
- ❌ `password` (too short, no uppercase, no digit, no special char)
- ❌ `Password123` (no special character)

---

## 🔄 Token Lifecycle

### Access Token
- **Lifetime:** 15 minutes (default)
- **Use:** Authorize API requests
- **Header:** `Authorization: Bearer <token>`
- **Revocation:** Immediate via jti cache

### Refresh Token
- **Lifetime:** 7 days (default)
- **Use:** Obtain new access tokens
- **Storage:** Database (admin_refresh_sessions)
- **Rotation:** Automatic on each refresh
- **Replay Detection:** Revokes entire session family

---

## 📋 API Endpoints Summary

### Authentication
```
POST   /api/admin/auth/login          # Login
POST   /api/admin/auth/refresh        # Refresh token
POST   /api/admin/auth/logout         # Logout
GET    /api/admin/auth/me             # Get profile
POST   /api/admin/auth/change-password # Change password
```

### Admin Management (super_admin only)
```
GET    /api/admin/admins              # List admins
POST   /api/admin/admins              # Create admin
PATCH  /api/admin/admins/{id}/status  # Activate/deactivate
DELETE /api/admin/admins/{id}/sessions # Revoke sessions
```

### Protected Endpoints (require appropriate permissions)
```
GET    /api/admin/tenants                                    # tenants:read
GET    /api/admin/tenants/{id}                               # tenants:read
PATCH  /api/admin/tenants/{id}/status                        # tenants:write
DELETE /api/admin/tenants/{id}                               # tenants:delete
GET    /api/admin/tenants/{id}/agents                        # agents:read
PATCH  /api/admin/tenants/{id}/agents/{id}/status            # agents:write
DELETE /api/admin/tenants/{id}/agents/{id}                   # agents:delete
GET    /api/admin/tenants/{id}/api-keys                      # api_keys:read
POST   /api/admin/tenants/{id}/api-keys/{kid}/revoke         # api_keys:revoke
POST   /api/admin/tenants/{id}/api-keys/revoke-all          # api_keys:revoke
DELETE /api/admin/tenants/{id}/conversations/{cid}           # conversations:delete
```

---

## 🐛 Troubleshooting

### "JWT_SECRET_KEY must be at least 32 characters"
**Solution:** Set a proper secret in `.env`:
```bash
MAAP_JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### "Invalid credentials" on login
**Causes:**
- Wrong username or password
- Account is deactivated (`is_active=false`)

**Check:**
```bash
# Via Docker
docker exec -it maap-backend python -c "
from backend.app.db.base import SessionLocal
from backend.app.db.models import AdminUser
db = SessionLocal()
admin = db.query(AdminUser).filter_by(username='youruser').first()
print(f'Active: {admin.is_active if admin else \"Not found\"}')"
```

### "Token expired"
**Solution:** Use the refresh token to get a new access token:
```bash
curl -X POST http://localhost:8000/api/admin/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "maap_adm_..."}'
```

### "Permission denied"
**Causes:**
- Current role doesn't have required permission
- Check your role: `GET /api/admin/auth/me`

**Solution:** Login as super_admin or request appropriate role

### Legacy key not working
**Check:** `MAAP_ADMIN_LEGACY_KEY_ENABLED` in `.env`
- If `false`, legacy X-Admin-Key header is disabled
- Use JWT authentication instead

---

## 🔒 Security Best Practices

### For Production

✅ **DO:**
- Use a strong, random JWT secret (32+ characters)
- Disable legacy key: `MAAP_ADMIN_LEGACY_KEY_ENABLED=false`
- Use HTTPS for all API requests
- Rotate JWT secret periodically
- Review audit logs regularly
- Deactivate unused accounts
- Use strong passwords

❌ **DON'T:**
- Share admin credentials
- Log tokens or passwords
- Use short JWT secrets
- Leave legacy key enabled
- Reuse passwords
- Skip password requirements

### Environment Checklist

**Development:**
- ✅ `MAAP_ADMIN_LEGACY_KEY_ENABLED=true` (optional)
- ✅ Short token lifetimes for testing

**Staging:**
- ✅ Same config as production
- ✅ Test with real-world scenarios
- ⚠️ Warning if legacy key enabled

**Production:**
- ✅ `MAAP_ADMIN_LEGACY_KEY_ENABLED=false`
- ✅ Strong JWT secret (32+ chars)
- ✅ HTTPS only
- ✅ Regular audit log reviews
- ✅ Backup strategy for admin_users table

---

## 📚 Additional Resources

**Documentation:**
- Full Report: `IMPLEMENTATION_REPORT_AR.md`
- Executive Summary: `EXECUTIVE_SUMMARY_AR.md`
- Requirements: `.kiro/specs/admin-auth-rbac/requirements.md`
- Design: `.kiro/specs/admin-auth-rbac/design.md`
- Tasks: `.kiro/specs/admin-auth-rbac/tasks.md`

**Standards:**
- [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [JWT Best Practices](https://datatracker.ietf.org/doc/html/rfc8725)
- [OWASP Authentication](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

---

## 💡 Common Workflows

### Daily Operations

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"pass"}' \
  | jq -r '.access_token')

# 2. Do your work
curl http://localhost:8000/api/admin/tenants \
  -H "Authorization: Bearer $TOKEN"

# 3. Logout when done
curl -X POST http://localhost:8000/api/admin/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

### Emergency: Revoke Compromised Account

```bash
# As super_admin, immediately revoke all sessions
curl -X DELETE http://localhost:8000/api/admin/admins/{compromised_id}/sessions \
  -H "Authorization: Bearer $SUPER_ADMIN_TOKEN"

# Then deactivate the account
curl -X PATCH http://localhost:8000/api/admin/admins/{compromised_id}/status \
  -H "Authorization: Bearer $SUPER_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

### Password Reset (self-service)

```bash
# User must know current password
curl -X POST http://localhost:8000/api/admin/auth/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "OldPassword123!",
    "new_password": "NewSecurePassword456!"
  }'

# All sessions are revoked; must login again
```

---

## ✅ Testing Your Setup

Run the comprehensive test suite:

```bash
# All tests
pytest backend/tests/

# Authentication tests only
pytest backend/tests/test_admin_auth.py -v

# RBAC tests only
pytest backend/tests/test_admin_rbac.py -v

# With coverage
pytest backend/tests/ --cov=backend/app --cov-report=html
```

**Expected Results:**
- ✅ 100+ tests pass
- ✅ No modifications to existing tests
- ✅ All 11 protected endpoints work
- ✅ All 3 roles behave correctly

---

## 🎯 Next Steps

1. **Review the full documentation** in `IMPLEMENTATION_REPORT_AR.md`
2. **Configure your environment** properly for production
3. **Create your admin accounts** with appropriate roles
4. **Test all workflows** in staging before production
5. **Set up monitoring** for failed login attempts
6. **Plan legacy key deprecation** timeline

---

**Status:** ✅ Ready for Production  
**Version:** 1.0  
**Last Updated:** August 1, 2026

