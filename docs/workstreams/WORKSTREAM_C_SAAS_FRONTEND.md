# Athka Chatbots — Workstream C: SaaS Frontend

## Branch

feature/phase1-saas-frontend

## Shared Baseline

49da1b1963384d3966c9b79d7765171711853892

Do not rebase this branch onto another developer branch.
Do not merge Workstream A or B yourself.

---

# Goal

Build the Phase 1 Athka Chatbots SaaS customer experience.

The user journey is:

Choose plan
→ Signup
→ Email verification
→ Athka review
→ Approval
→ Login
→ Tenant Portal

Keep the experience simple and visually clear.

---

# Brand

Customer-facing product name:

Athka Chatbots

Do not expose internal terms such as:

- MAAP
- Agent IDs
- Knowledge Base IDs
- Tenant IDs

Customer terminology:

- Chatbot
- Company
- Knowledge
- Conversations
- Appearance
- Deployment

---

# Phase 1 Public Pages

Implement the frontend experience for:

- public entry / pricing CTA
- signup
- email verification
- login
- application-status screen

Do not build the Chatbot Wizard yet.

---

# Signup UX

The signup form must remain short.

Required fields:

- name
- email
- company name
- password
- selected/requested plan
- legal/pricing acceptance

Do NOT add:

- company size
- message-volume questions
- number of websites
- detailed use-case questionnaire
- language questionnaire

Those belong to progressive onboarding later.

---

# Application States

The UI must support:

- email_pending
- under_review
- changes_requested
- approved
- rejected

Before approval the customer must NOT see the full Tenant Portal.

They may authenticate only sufficiently to see the application state when supported by the backend contracts.

---

# Tenant Portal Shell

Build the authenticated customer shell for `/app`.

Prepare navigation for future customer areas such as:

- Overview
- Chatbots
- Knowledge
- Conversations
- Team
- Account

Only Phase 1 functionality needs to work now.

Do not implement the Chatbot creation Wizard in this workstream.

---

# Admin Application Review UI

Add an Athka Platform Admin screen for customer applications.

It must support displaying:

- applicant
- company
- requested plan
- email verification state
- application status
- submission time
- review information

Actions:

- approve
- reject
- request changes

Use existing Admin authentication/RBAC.

Do not create a second Admin authentication frontend.

---

# Expected API Contracts

Workstream A owns onboarding/approval backend.

Frontend should centralize these calls rather than scattering fetch requests.

Expected conceptual endpoints:

- POST /api/v1/saas/signup
- POST /api/v1/saas/verify-email
- GET /api/v1/saas/application/status

Admin:

- GET /api/v1/admin/tenant-applications
- GET /api/v1/admin/tenant-applications/{application_id}
- POST /api/v1/admin/tenant-applications/{application_id}/approve
- POST /api/v1/admin/tenant-applications/{application_id}/reject
- POST /api/v1/admin/tenant-applications/{application_id}/request-changes

Workstream B owns customer authentication.

Expected conceptual endpoints:

- POST /api/v1/tenant-auth/login
- POST /api/v1/tenant-auth/refresh
- POST /api/v1/tenant-auth/logout
- GET /api/v1/tenant-auth/me

If repository-wide prefixes are already provided by the API router, follow the real API convention without duplicating prefixes.

Keep API calls behind a small typed client layer so final route adjustments are localized.

---

# Frontend States

Every network-backed page should handle:

- loading
- success
- validation error
- unauthorized
- forbidden
- server error

Do not silently fail.

Do not expose raw backend stack traces or internal identifiers.

---

# Route Protection

Customer `/app` routes must not rely only on hiding navigation.

Unauthenticated users must be redirected appropriately.

Pending/unapproved customers must not receive normal Tenant Portal access.

Admin application-review routes must remain protected by existing Admin authentication.

---

# Expected Frontend Areas

Likely modifications/new files under:

- frontend/src/app/
- frontend/src/components/
- frontend/src/lib/

Prefer reusable components and typed API clients.

Keep existing frontend architecture unless there is a clear reason to change it.

---

# Do Not Modify

- backend/*
- Alembic migrations
- SQLAlchemy models
- customer authentication implementation
- onboarding backend operations
- approval transaction logic
- Admin security implementation

Do not create mock backend logic inside production frontend code.

---

# Out of Scope

Do NOT implement:

- Chatbot Wizard
- billing provider
- payment processing
- Stripe integration
- WordPress plugin
- Hosted Chat
- team invitations
- usage billing
- production AI-provider configuration

---

# Required Validation

Run the repository's existing frontend checks.

At minimum:

- lint
- TypeScript/typecheck
- production build

Also verify manually:

- signup screen
- verify-email screen
- review/pending state
- rejection state
- login screen
- protected /app shell
- Admin applications screen
- responsive layout

---

# Definition of Done

Workstream C is complete when:

- Phase 1 customer journey exists visually
- signup is intentionally minimal
- approval states are clear
- Tenant Portal shell exists
- protected route behavior exists
- Admin application review UI exists
- API access is centralized
- no backend files were modified
- lint/typecheck/build pass
- branch is pushed

---

# Delivery

Do NOT merge into feature/saas-tenant-portal.

When finished provide:

1. branch name
2. final commit hash
3. screenshots of main screens
4. changed-file summary
5. lint result
6. typecheck result
7. build result
8. assumptions
9. known limitations

Athka team will review the branch before merge.
