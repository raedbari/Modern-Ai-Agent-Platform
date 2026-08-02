/**
 * Admin API Client
 * SERVER-SIDE ONLY - Contains admin credentials
 */

export const ADMIN_API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

if (typeof window !== 'undefined') {
  console.error('[SECURITY] Admin client in browser!');
}

export const AdminPaths = {
  "/api/admin/admins": "/api/admin/admins",
  "/api/admin/admins/{admin_id}/sessions": "/api/admin/admins/{admin_id}/sessions",
  "/api/admin/admins/{admin_id}/status": "/api/admin/admins/{admin_id}/status",
  "/api/admin/audit": "/api/admin/audit",
  "/api/admin/auth/change-password": "/api/admin/auth/change-password",
  "/api/admin/auth/login": "/api/admin/auth/login",
  "/api/admin/auth/logout": "/api/admin/auth/logout",
  "/api/admin/auth/me": "/api/admin/auth/me",
  "/api/admin/auth/refresh": "/api/admin/auth/refresh",
  "/api/admin/tenants": "/api/admin/tenants",
  "/api/admin/tenants/{tenant_id}": "/api/admin/tenants/{tenant_id}",
  "/api/admin/tenants/{tenant_id}/agents": "/api/admin/tenants/{tenant_id}/agents",
  "/api/admin/tenants/{tenant_id}/agents/{agent_id}": "/api/admin/tenants/{tenant_id}/agents/{agent_id}",
  "/api/admin/tenants/{tenant_id}/agents/{agent_id}/status": "/api/admin/tenants/{tenant_id}/agents/{agent_id}/status",
  "/api/admin/tenants/{tenant_id}/agents/{agent_id}/widget": "/api/admin/tenants/{tenant_id}/agents/{agent_id}/widget",
  "/api/admin/tenants/{tenant_id}/api-keys": "/api/admin/tenants/{tenant_id}/api-keys",
  "/api/admin/tenants/{tenant_id}/api-keys/revoke-all": "/api/admin/tenants/{tenant_id}/api-keys/revoke-all",
  "/api/admin/tenants/{tenant_id}/api-keys/{key_id}/revoke": "/api/admin/tenants/{tenant_id}/api-keys/{key_id}/revoke",
  "/api/admin/tenants/{tenant_id}/conversations/{conversation_id}": "/api/admin/tenants/{tenant_id}/conversations/{conversation_id}",
  "/api/admin/tenants/{tenant_id}/status": "/api/admin/tenants/{tenant_id}/status",
  "/api/chat": "/api/chat",
  "/api/knowledge-bases": "/api/knowledge-bases",
  "/api/knowledge-bases/{knowledge_base_id}": "/api/knowledge-bases/{knowledge_base_id}",
  "/api/knowledge-bases/{knowledge_base_id}/document-jobs": "/api/knowledge-bases/{knowledge_base_id}/document-jobs",
  "/api/knowledge-bases/{knowledge_base_id}/document-jobs/{job_id}": "/api/knowledge-bases/{knowledge_base_id}/document-jobs/{job_id}",
  "/api/knowledge-bases/{knowledge_base_id}/documents": "/api/knowledge-bases/{knowledge_base_id}/documents",
  "/api/knowledge-bases/{knowledge_base_id}/documents/{document_id}": "/api/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
  "/api/knowledge-bases/{knowledge_base_id}/documents/{document_id}/reindex": "/api/knowledge-bases/{knowledge_base_id}/documents/{document_id}/reindex",
  "/health": "/health",
  "/ready": "/ready",
} as const;
