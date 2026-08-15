# Athka CI/CD Foundation v1

Required PR gates:
- policy-gates
- frontend-quality
- backend-db-rag

The architecture policy starts in transition mode: it blocks NEW provider
coupling without pretending the legacy pilot is already fully modularized.

Security CodeQL is separate. Make it required only after it has run successfully
with the final repository visibility/plan.

Next gates:
- OpenAPI drift/regeneration
- dedicated cross-tenant isolation suite
- Golden Questions evaluation regression
- AI cost/budget regression
- destructive migration approvals
- staging deployment
- production approval + rollback
