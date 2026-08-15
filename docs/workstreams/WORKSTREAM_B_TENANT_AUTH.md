# Athka Chatbots — Workstream B: Tenant Authentication

## Branch

feature/phase1-tenant-auth

## Shared Baseline

49da1b1963384d3966c9b79d7765171711853892

Do not rebase this branch onto another developer branch.
Do not merge Workstream A or C yourself.

---

# Goal

Build secure authentication and authorization for Athka customer users.

This authentication system is completely separate from Athka Platform Admin authentication.

Do NOT reuse `admin_users` as customer identities.

Existing customer identity tables are already available:

- users
- user_refresh_sessions
- tenant_memberships
- tenants

---

# Required Flow

User credentials
→ customer authentication
→ active user validation
→ active refresh-session family
→ active tenant membership
→ active tenant
→ authoritative current membership role
→ TenantUserContext
→ authorized tenant request

JWT claims alone are never authoritative.

---

# Required API

Implement customer-facing authentication equivalent to:

- POST /api/v1/tenant-auth/login
- POST /api/v1/tenant-auth/refresh
- POST /api/v1/tenant-auth/logout
- GET /api/v1/tenant-auth/me

`/me` must support both pre-approval and approved users.

It should return the authenticated user plus:

- current tenant application status when present
- active membership/tenant information when present

A verified user with an application in `under_review` may use `/me`
but must not receive TenantUserContext until an active membership exists.

Follow the repository's existing FastAPI routing conventions if the common API prefix is already applied elsewhere.

## Login

Input:

- email
- password

Requirements:

- normalize email before lookup
- reject inactive users
- reject users without verified email
- verify Argon2 password
- require an active TenantMembership
- require active Tenant
- create database-backed refresh session
- return short-lived access token
- return refresh token

Phase 1 normally has one active TenantMembership after approval.

Do not permanently design the security model around one tenant per user; the schema intentionally supports multiple memberships.

---

# Token Security

Reuse the security architecture/patterns already proven by Admin Auth where appropriate.

Required:

- short-lived access JWT
- database-backed refresh sessions
- refresh-token rotation
- session family_id
- replay detection
- family revocation on replay
- raw refresh token must never be stored
- store SHA-256 token hash only
- expiry validation
- revoked session validation
- secure JWT algorithm configuration
- login rate limiting

Changing password, disabling user, revoking membership, suspending membership, or disabling Tenant must invalidate effective access without waiting for JWT expiry.

---

# TenantUserContext

Create a customer context separate from AdminContext.

The protected request path must validate authoritative database state:

1. JWT is cryptographically valid
2. User exists
3. User is active
4. Relevant session family is active and unexpired
5. TenantMembership exists
6. Membership status is active
7. Tenant exists
8. Tenant is active
9. Current role comes from database membership
10. Request continues

Never trust tenant_id or role from the browser without database validation.

---

# Tenant RBAC

Prepare a customer permission model separate from Admin RBAC.

Initial roles already defined by the schema:

- tenant_owner
- tenant_admin
- knowledge_editor
- conversation_viewer
- billing_manager

Keep permission definitions centralized.

Do not reuse Platform Admin roles:

- super_admin
- operator
- auditor

Suggested future permission namespace:

- chatbots:read
- chatbots:write
- knowledge:read
- knowledge:write
- conversations:read
- members:read
- members:write
- billing:read
- billing:write

Implement only what Phase 1 requires, but structure it so additional permissions do not require redesigning authentication.

---

# Expected Backend Areas

Prefer new customer-specific modules instead of modifying Admin Auth directly.

Likely areas:

- backend/app/auth/
- backend/app/api/routes/
- backend/app/schemas/
- backend/app/operations/
- backend/tests/

Use repository naming conventions.

---

# Do Not Modify

Unless absolutely necessary and documented:

- backend/alembic/versions/*
- customer identity database schema
- tenant application schema
- legal acceptance schema
- onboarding approval workflow
- frontend/*
- Admin Auth semantics
- Widget authentication semantics

Do not create another User table.

Do not add tenant_id directly to users.

---

# Required Tests

At minimum cover:

- valid login
- wrong password
- unknown email
- unverified email
- inactive user
- inactive tenant
- suspended membership
- revoked membership
- access token validation
- refresh rotation
- refresh replay detection
- logout/revocation
- password-change invalidation
- user deactivation invalidation
- membership-role changes take immediate effect
- tenant isolation
- Admin Auth regression remains green

Run existing Admin Auth/security regression tests as well.

---

# Definition of Done

Workstream B is complete only when:

- customer login works
- refresh works securely
- logout revokes session
- /me returns authenticated customer context
- TenantUserContext uses authoritative DB state
- tenant isolation tests pass
- no Admin Auth regression
- no schema migration was introduced without explicit justification
- diff --check passes
- branch is pushed

---

# Delivery

Do NOT merge into feature/saas-tenant-portal.

When finished provide:

1. branch name
2. final commit hash
3. changed-file summary
4. tests executed
5. passed/failed counts
6. security decisions
7. any assumptions
8. any known limitations

Athka team will review the branch before merge.

