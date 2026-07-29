# 07-security: Security Policies and Practices

## Purpose

This document defines security policies and practices for the Modern AI Agent Platform. It establishes authentication and authorization patterns, secret management rules, tenant isolation enforcement, input validation requirements, API security practices, logging security, and widget security. This document focuses exclusively on security—protecting the platform, tenant data, and user privacy.

## Security Principles

### Security by Default

Security is not optional or added later. Every component, every layer, and every operation enforces security by default. Operations without proper authentication, authorization, or tenant context are rejected.

### Defense in Depth

Security is enforced at multiple layers. If one layer fails, other layers provide protection. Authentication, authorization, input validation, tenant isolation, and logging work together to create a secure system.

### Least Privilege

Users and systems are granted the minimum permissions necessary to perform their functions. No entity has more access than required.

### Fail Securely

When errors occur, the system fails in a secure state. Errors do not expose sensitive data, bypass security checks, or grant unintended access.

### Explicit Authorization

Authorization is never implicit or assumed. Every operation explicitly checks authorization. No operation proceeds without verified permission.

## Authentication

Authentication verifies the identity of users and systems accessing the platform.

### User Authentication

**Tenant Users**:
- Authenticate using email and password (initial implementation)
- Passwords are hashed using bcrypt or Argon2 (never stored in plaintext)
- Multi-factor authentication (MFA) support planned for later phase
- Session tokens are issued upon successful authentication
- Sessions expire after inactivity period (configurable, default 24 hours)

**Website Visitors**:
- No authentication required to interact with Chat Widgets
- Anonymous sessions tracked by session ID for conversation continuity
- No personal data collected without explicit consent

**Platform Administrators**:
- Elevated authentication requirements (MFA mandatory)
- Separate authentication mechanism from Tenant Users
- Admin access is audited and logged

### Token-Based Authentication

**JSON Web Tokens (JWT)**:
- Issued upon successful authentication
- Contain user identity and tenant context
- Signed with platform secret key (MAAP_SECRET_KEY)
- Short-lived access tokens (1 hour)
- Refresh tokens for session renewal (24 hours)

**Token Structure**:
```json
{
  "sub": "user_id",
  "tenant_id": "tenant_123",
  "role": "tenant_user",
  "exp": 1672531200
}
```

**Token Validation**:
- Verify token signature using secret key
- Check expiration timestamp
- Extract tenant context from token
- Reject invalid or expired tokens

### API Authentication

All API requests (except public endpoints like health checks) require authentication:

**Authentication Header**:
```
Authorization: Bearer <access_token>
```

**Authentication Middleware**:
- Extracts token from Authorization header
- Validates token signature and expiration
- Establishes tenant context from token
- Rejects requests without valid token

## Authorization

Authorization determines what authenticated users are permitted to do.

### Role-Based Access Control

**Roles**:
- **Platform Administrator**: Manages the entire platform, monitors system health, oversees tenant operations
- **Tenant User**: Manages agents, uploads knowledge, configures widgets within their tenant
- **Website Visitor**: Interacts with Chat Widgets (no account required)

**Permissions**:
- Platform Administrators: Full platform access, tenant oversight (operational only)
- Tenant Users: Full access to their tenant's agents, knowledge, configurations (no access to other tenants)
- Website Visitors: Read-only access to public Chat Widget interfaces

### Tenant Isolation Enforcement

**Mandatory Authorization Checks**:
- Every operation accessing tenant data must verify tenant ownership
- Extract tenant ID from authentication token
- Verify requested resource belongs to the authenticated tenant
- Reject requests accessing data from other tenants

**Authorization Pattern**:
```python
def get_agent(agent_id: str, tenant_context: TenantContext) -> Agent:
    # Retrieve agent
    agent = agent_repository.find_by_id(agent_id)
    
    # Authorization check: Verify tenant ownership
    if agent.tenant_id != tenant_context.tenant_id:
        raise UnauthorizedAccessException(
            f"Agent {agent_id} does not belong to tenant {tenant_context.tenant_id}"
        )
    
    return agent
```

### Agent Isolation Enforcement

**Knowledge Access Authorization**:
- Knowledge retrieval is scoped by tenant ID and agent ID
- Tenant Users can only access knowledge from their own agents
- Cross-agent knowledge access is prohibited

**Conversation Access Authorization**:
- Conversations belong to a specific agent
- Tenant Users can only access conversations from their own agents
- Cross-agent conversation access is prohibited

### Operation-Level Authorization

**Create Operations**:
- Verify user has permission to create resources within their tenant
- Tenant context is mandatory for all create operations

**Read Operations**:
- Verify user has permission to read the resource
- Verify resource belongs to user's tenant

**Update Operations**:
- Verify user has permission to update the resource
- Verify resource belongs to user's tenant

**Delete Operations**:
- Verify user has permission to delete the resource
- Verify resource belongs to user's tenant

### Authorization Decision Pattern

Every authorization decision follows this pattern:
1. Authenticate user and establish tenant context
2. Retrieve requested resource
3. Verify resource belongs to user's tenant
4. Verify user has permission for the requested operation
5. Allow operation if all checks pass
6. Reject and log if any check fails

## Secret Management

Secrets are sensitive values that must never be exposed. This includes API keys, database passwords, encryption keys, and authentication tokens.

### Environment Variables

**All secrets are stored in environment variables**:
- Never hardcode secrets in source code
- Never commit secrets to version control
- Use `.env` files for local development (excluded from Git)
- Use secure secret management systems for production (AWS Secrets Manager, Azure Key Vault, etc.)

**Environment Variable Naming**:
- Use `MAAP_` prefix for all platform-specific variables
- Use descriptive names (MAAP_DATABASE_PASSWORD, not MAAP_DB_PW)

**Example**:
```bash
MAAP_DATABASE_URL=postgresql://localhost/maap
MAAP_DATABASE_PASSWORD=secure_password_here
MAAP_SECRET_KEY=long_random_secret_key_for_jwt_signing
MAAP_AI_API_KEY=sk-provider_api_key_here
```

### Secret Rotation

- Secrets should be rotated periodically
- Platform must support secret rotation without downtime
- Old secrets are invalidated after rotation grace period

### Secret Access Control

- Secrets are accessible only to services that need them
- Secrets are not exposed in logs, error messages, or API responses
- Secrets are not passed as URL parameters or stored in cookies

See #[[file:03-system-architecture.md]] for configuration management patterns.

## Input Validation

Input validation is the first line of defense against attacks. All external input must be validated before processing.

### Validation Rules

**Validate at System Boundaries**:
- Validate all input at API endpoints
- Never trust client-provided data
- Validate before processing, not after

**Validate Everything**:
- Request bodies
- URL parameters
- Query strings
- Headers
- File uploads

**Validation Criteria**:
- Type correctness (string, integer, boolean, etc.)
- Length limits (minimum, maximum)
- Format constraints (email, URL, date, etc.)
- Allowed values (enums, whitelists)
- Required vs optional fields

### Validation Implementation

**Backend Validation (Python/FastAPI)**:
```python
from pydantic import BaseModel, Field, validator

class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    instructions: str = Field(..., min_length=10, max_length=5000)
    
    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()
```

**Frontend Validation (TypeScript/Zod)**:
```typescript
import { z } from 'zod';

const createAgentSchema = z.object({
  name: z.string().min(3).max(100),
  instructions: z.string().min(10).max(5000),
});
```

### Sanitization

**Sanitize Input**:
- Remove or escape potentially dangerous characters
- Normalize input (trim whitespace, convert to lowercase if appropriate)
- Encode output to prevent injection attacks

**SQL Injection Prevention**:
- Use parameterized queries or ORM (never raw SQL with string interpolation)
- Validate and sanitize all database inputs

**XSS Prevention**:
- Escape HTML output
- Use Content Security Policy (CSP) headers
- Sanitize user-generated content before display

## API Security

### HTTPS Only

- All API communication must use HTTPS
- HTTP requests are redirected to HTTPS
- No sensitive data transmitted over unencrypted connections

### CORS (Cross-Origin Resource Sharing)

**CORS Configuration**:
- Allow requests only from trusted origins
- Configure allowed methods (GET, POST, PUT, DELETE)
- Configure allowed headers
- Do not use wildcard (`*`) for production

**Example**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Rate Limiting

**Prevent Abuse**:
- Limit API requests per user/IP address
- Use rate limiting for authentication endpoints (prevent brute force)
- Use rate limiting for expensive operations (knowledge upload, RAG pipeline)

**Rate Limiting Patterns**:
- Fixed window: X requests per time window
- Sliding window: X requests per rolling time window
- Token bucket: Flexible burst handling

**Rate Limiting Configuration**:
```bash
MAAP_RATE_LIMIT_AUTH=5/minute
MAAP_RATE_LIMIT_API=100/minute
MAAP_RATE_LIMIT_UPLOAD=10/hour
```

### Request Size Limits

- Limit request body size to prevent resource exhaustion
- Limit file upload size (e.g., max 10 MB per document)
- Return appropriate error messages when limits are exceeded

**Configuration**:
```bash
MAAP_MAX_REQUEST_SIZE=10MB
MAAP_MAX_UPLOAD_SIZE=10MB
```

### Security Headers

**Required Security Headers**:
- `Content-Security-Policy`: Prevents XSS and injection attacks
- `X-Content-Type-Options: nosniff`: Prevents MIME type sniffing
- `X-Frame-Options: DENY`: Prevents clickjacking
- `X-XSS-Protection: 1; mode=block`: Enables browser XSS protection
- `Strict-Transport-Security`: Enforces HTTPS

**Example**:
```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

## Logging Security

Logging is essential for monitoring and debugging, but improper logging creates security vulnerabilities.

### Never Log Secrets

**Never log**:
- Passwords (plaintext or hashed)
- API keys
- Access tokens or refresh tokens
- Database passwords
- Encryption keys
- Credit card numbers or payment information
- Social Security numbers or personal identification numbers

**Mask Sensitive Data**:
- If you must log a reference to a secret (e.g., API key ID), mask all but the last few characters
- Example: `api_key=***ab12` instead of `api_key=sk-1234567890abcdef`

### Log Security Events

**Audit Security-Relevant Events**:
- Authentication attempts (success and failure)
- Authorization failures
- Resource access (who accessed what, when)
- Configuration changes
- Admin actions
- Suspicious activity (repeated failures, unusual patterns)

**Audit Log Structure**:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "event": "authentication_success",
  "user_id": "user_123",
  "tenant_id": "tenant_456",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 ..."
}
```

### Log Enough Context

**Include Identifiers, Not Content**:
- Log tenant ID, agent ID, user ID, operation type
- Do not log message content, document text, or user input
- Do not log retrieved knowledge chunks
- Do not log AI-generated responses

**Example**:
```python
# CORRECT: Log identifiers
logger.info(
    "Knowledge retrieval completed",
    extra={
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "result_count": len(chunks),
        "duration_ms": duration_ms
    }
)

# WRONG: Log sensitive content
logger.info(f"User message: {user_message}")  # Don't do this!
logger.info(f"AI response: {response}")       # Don't do this!
```

### Log Retention and Access

- Logs are retained according to compliance requirements
- Access to logs is restricted to authorized personnel
- Logs containing security events are stored securely and protected from tampering

## Data Privacy and Compliance

### Tenant Data Isolation

- Tenant data is logically separated in the database
- All queries are scoped by tenant ID
- Cross-tenant data access is prohibited
- Tenant data is encrypted at rest (database encryption)

### Data Retention

**Knowledge Data**:
- Tenant owns their knowledge data
- Knowledge is retained as long as the tenant's account is active
- Knowledge is deleted when the tenant deletes an agent or terminates their account

**Conversation Data**:
- Conversations are retained for a configurable period (default: 90 days)
- Old conversations may be archived or deleted
- Retention policies are configurable per tenant (if required)

**User Data**:
- User accounts are retained as long as they are active
- Inactive accounts may be deactivated after a period of inactivity
- Deleted accounts are permanently removed following a grace period

### Data Deletion

**Right to Deletion**:
- Tenants can delete their data at any time
- Data deletion is permanent and irreversible
- Deletion is audited and logged

**Deletion Process**:
- Tenant requests data deletion
- Platform administrator verifies request
- All tenant data (agents, knowledge, conversations, configurations) is deleted
- Deletion is confirmed to the tenant

## Widget Security

Chat Widgets are embedded on tenant websites and interact with Website Visitors. Widget security ensures safe embedding and prevents abuse.

### Embedding Security

**CORS Configuration**:
- Allow embedding only from tenant-configured domains
- Verify origin header for widget requests
- Reject requests from unauthorized origins

**Content Security Policy (CSP)**:
- Define CSP headers for widget content
- Restrict script sources, styles, and frames
- Prevent injection attacks through widget

### Session Security

**Anonymous Sessions**:
- Website Visitors interact with widgets without authentication
- Sessions are identified by session ID (generated client-side or server-side)
- Session IDs are not predictable (use UUIDs or secure random strings)

**Session Hijacking Prevention**:
- Session IDs are not exposed in URLs
- Session IDs are transmitted over HTTPS only
- Session IDs expire after inactivity period

### Rate Limiting for Widgets

- Limit requests per session to prevent abuse
- Limit requests per IP address to prevent DoS attacks
- Block or throttle abusive sessions

### Message Validation

**Validate All Input**:
- Validate message length (e.g., max 1000 characters)
- Validate message format (text only, no scripts or HTML)
- Reject invalid or malicious input

**Content Filtering**:
- Filter or block inappropriate language
- Block known attack patterns (SQL injection, XSS attempts)
- Log suspicious input for review

## Incident Response

### Detecting Security Incidents

**Monitor for**:
- Repeated authentication failures
- Authorization failures (users attempting to access other tenants' data)
- Unusual API usage patterns
- Suspicious input (injection attempts)
- Large data access or exports
- Configuration changes by unauthorized users

### Responding to Incidents

**Immediate Actions**:
1. Detect and alert on security event
2. Investigate and assess impact
3. Contain the incident (disable compromised accounts, block malicious IPs)
4. Notify affected tenants if data was accessed
5. Document the incident and response

**Post-Incident Actions**:
1. Conduct root cause analysis
2. Implement fixes to prevent recurrence
3. Update security policies and procedures
4. Train team on lessons learned

### Security Testing

- Regular security testing (penetration testing, vulnerability scanning)
- Automated security checks in CI/CD pipeline
- Code review with security focus
- Dependency vulnerability scanning

## Common Security Vulnerabilities

### SQL Injection

**Prevention**:
- Use parameterized queries or ORM
- Never construct SQL queries with string interpolation
- Validate and sanitize all input

**Example**:
```python
# WRONG: SQL injection vulnerability
query = f"SELECT * FROM agents WHERE id = '{agent_id}'"

# CORRECT: Parameterized query
query = "SELECT * FROM agents WHERE id = %s"
cursor.execute(query, (agent_id,))
```

### Cross-Site Scripting (XSS)

**Prevention**:
- Escape HTML output
- Use Content Security Policy (CSP) headers
- Sanitize user-generated content before display

### Cross-Site Request Forgery (CSRF)

**Prevention**:
- Use CSRF tokens for state-changing operations
- Verify origin and referer headers
- Use SameSite cookie attributes

### Authentication Bypass

**Prevention**:
- Enforce authentication on all protected endpoints
- Validate authentication tokens on every request
- Never rely on client-side authentication

### Authorization Bypass

**Prevention**:
- Verify tenant ownership before all operations
- Never trust client-provided tenant ID
- Extract tenant context from authenticated token

### Insecure Direct Object References (IDOR)

**Prevention**:
- Verify user has permission to access requested resource
- Do not expose internal IDs without authorization checks

**Example**:
```python
# WRONG: No authorization check
@router.get("/agents/{agent_id}")
def get_agent(agent_id: str):
    return agent_repository.find_by_id(agent_id)  # Any user can access any agent!

# CORRECT: Verify tenant ownership
@router.get("/agents/{agent_id}")
def get_agent(agent_id: str, tenant_context: TenantContext):
    agent = agent_repository.find_by_id(agent_id)
    if agent.tenant_id != tenant_context.tenant_id:
        raise UnauthorizedAccessException("Access denied")
    return agent
```

## Security Checklist

Use this checklist when implementing features or reviewing code:

- [ ] Authentication is required for protected operations
- [ ] Tenant context is established and verified
- [ ] Tenant ownership is verified before operations
- [ ] All input is validated at system boundaries
- [ ] Secrets are stored in environment variables, not code
- [ ] Secrets are not logged or exposed in error messages
- [ ] SQL queries use parameterization, not string interpolation
- [ ] Authorization is explicit and checked on every operation
- [ ] HTTPS is enforced for all API communication
- [ ] CORS is configured to allow only trusted origins
- [ ] Rate limiting is implemented for sensitive operations
- [ ] Security headers are included in API responses
- [ ] Security events are logged for audit
- [ ] User input is sanitized to prevent XSS
- [ ] Session tokens are secure and expire appropriately

## References

- Configuration management: #[[file:03-system-architecture.md]]
- Testing security: #[[file:08-testing.md]]
- Domain model and tenant isolation: #[[file:02-domain-model.md]]
- Coding standards for security: #[[file:04-coding-standards.md]]

## Document Boundaries

This document defines security policies and practices only. It establishes how to protect the platform, tenant data, and user privacy.

**This document must never contain:**

- **Implementation code**: Specific implementations, class definitions, or function signatures belong in source code.
- **Testing strategies**: General testing philosophy, test types, or coverage requirements belong in #[[file:08-testing.md]].
- **Architecture**: System layers, component boundaries, or dependency rules belong in #[[file:03-system-architecture.md]].
- **Domain model**: Entity definitions, relationships, or business rules belong in #[[file:02-domain-model.md]].
- **Coding standards**: General code quality, naming conventions, or organization rules belong in #[[file:04-coding-standards.md]].

This document focuses exclusively on **security** (authentication, authorization, secrets management, input validation, API security, logging security, incident response, and vulnerability prevention).

When questions arise about other topics, refer to the appropriate steering document.
