import "server-only";

import type {
  components,
} from "@/lib/api/generated/admin-api";

import { getApiBaseUrl } from "./config";

export type LoginRequest =
  components["schemas"]["LoginRequest"];

export type LoginResponse =
  components["schemas"]["LoginResponse"];

export type AdminProfile =
  components["schemas"]["AdminProfileResponse"];


export type TenantAdmin =
  components["schemas"]["TenantAdminResponse"];

export type AgentAdmin =
  components["schemas"]["AgentAdminResponse"];

export type ApiKeyAdmin =
  components["schemas"]["ApiKeyAdminResponse"];

export type AdminAuditEvent =
  components["schemas"]["AdminAuditEventResponse"];

type ErrorPayload = {
  detail?: unknown;
};

export class AdminApiError extends Error {
  readonly status: number;
  readonly detail: unknown;
  readonly retryAfter: string | null;

  constructor(
    status: number,
    detail: unknown,
    retryAfter: string | null = null,
  ) {
    super(
      typeof detail === "string"
        ? detail
        : `Admin API request failed with status ${status}.`,
    );

    this.name = "AdminApiError";
    this.status = status;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }
}

export class AdminApiUnavailableError extends Error {
  constructor(cause?: unknown) {
    super("The Admin API is currently unavailable.", {
      cause,
    });

    this.name = "AdminApiUnavailableError";
  }
}

function buildUrl(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(
      `Admin API path must start with "/": ${path}`,
    );
  }

  return `${getApiBaseUrl()}${path}`;
}

async function readResponseBody(
  response: Response,
): Promise<unknown> {
  const text = await response.text();

  if (!text) {
    return undefined;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function requestAdminApi<T>(
  path: string,
  init: RequestInit,
): Promise<T> {
  const headers = new Headers(init.headers);

  headers.set("Accept", "application/json");

  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;

  try {
    response = await fetch(buildUrl(path), {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch (error) {
    throw new AdminApiUnavailableError(error);
  }

  const body = await readResponseBody(response);

  if (!response.ok) {
    const payload =
      body !== null &&
      typeof body === "object"
        ? body as ErrorPayload
        : undefined;

    throw new AdminApiError(
      response.status,
      payload?.detail ?? body ?? response.statusText,
      response.headers.get("retry-after"),
    );
  }

  return body as T;
}

function bearerHeaders(
  accessToken: string,
): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
  };
}

export type RevokeAllApiKeysResult =
  components["schemas"]["RevokeAllApiKeysResponse"];


export type AgentConfigUpdatePayload =
  components["schemas"]["AgentConfigUpdate"];

export type AgentConfig =
  components["schemas"]["AgentConfigResponse"];

export type WidgetSettings =
  components["schemas"]["WidgetSettingsResponse"];

export type WidgetSettingsUpdatePayload =
  components["schemas"]["WidgetSettingsUpdate"];

export type KnowledgeBaseAdmin =
  components["schemas"]["KnowledgeBaseAdminResponse"];

export type KnowledgeDocumentAdmin =
  components["schemas"]["DocumentAdminResponse"];

export type KnowledgeIngestionJobAdmin =
  components["schemas"]["IngestionJobAdminResponse"];

export async function loginAdmin(
  payload: LoginRequest,
): Promise<LoginResponse> {
  return requestAdminApi<LoginResponse>(
    "/api/admin/auth/login",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function refreshAdminTokens(
  refreshToken: string,
): Promise<LoginResponse> {
  return requestAdminApi<LoginResponse>(
    "/api/admin/auth/refresh",
    {
      method: "POST",
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    },
  );
}

export async function getAdminProfile(
  accessToken: string,
): Promise<AdminProfile> {
  return requestAdminApi<AdminProfile>(
    "/api/admin/auth/me",
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function logoutAdmin(
  accessToken: string,
  refreshToken: string,
): Promise<{ detail: string }> {
  return requestAdminApi<{ detail: string }>(
    "/api/admin/auth/logout",
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    },
  );
}

export async function listAdminTenants(
  accessToken: string,
): Promise<TenantAdmin[]> {
  return requestAdminApi<TenantAdmin[]>(
    "/api/admin/tenants",
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function listTenantAgents(
  accessToken: string,
  tenantId: string,
): Promise<AgentAdmin[]> {
  return requestAdminApi<AgentAdmin[]>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/agents`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function listTenantApiKeys(
  accessToken: string,
  tenantId: string,
): Promise<ApiKeyAdmin[]> {
  return requestAdminApi<ApiKeyAdmin[]>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/api-keys`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function listAdminAuditEvents(
  accessToken: string,
  limit = 12,
): Promise<AdminAuditEvent[]> {
  const normalizedLimit = Math.min(
    Math.max(Math.trunc(limit), 1),
    100,
  );

  return requestAdminApi<AdminAuditEvent[]>(
    `/api/admin/audit?limit=${normalizedLimit}`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function updateAdminAgentStatus(
  accessToken: string,
  tenantId: string,
  agentId: string,
  isActive: boolean,
): Promise<AgentAdmin> {
  return requestAdminApi<AgentAdmin>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/agents/${
      encodeURIComponent(agentId)
    }/status`,
    {
      method: "PATCH",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify({
        is_active: isActive,
      }),
    },
  );
}

export async function updateAdminAgentConfiguration(
  accessToken: string,
  tenantId: string,
  agentId: string,
  payload: AgentConfigUpdatePayload,
): Promise<AgentConfig> {
  return requestAdminApi<AgentConfig>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/agents/${
      encodeURIComponent(agentId)
    }/config`,
    {
      method: "PATCH",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify(payload),
    },
  );
}

export async function getAdminWidgetSettings(
  accessToken: string,
  tenantId: string,
  agentId: string,
): Promise<WidgetSettings> {
  return requestAdminApi<WidgetSettings>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/agents/${
      encodeURIComponent(agentId)
    }/widget`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function putAdminWidgetSettings(
  accessToken: string,
  tenantId: string,
  agentId: string,
  payload: WidgetSettingsUpdatePayload,
): Promise<WidgetSettings> {
  return requestAdminApi<WidgetSettings>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/agents/${
      encodeURIComponent(agentId)
    }/widget`,
    {
      method: "PUT",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify(payload),
    },
  );
}



export async function listAdminKnowledgeBases(
  accessToken: string,
  tenantId: string,
  agentId?: string,
): Promise<KnowledgeBaseAdmin[]> {
  const searchParams =
    new URLSearchParams();

  if (agentId) {
    searchParams.set(
      "agent_id",
      agentId,
    );
  }

  const queryString =
    searchParams.toString();

  const query = queryString
    ? `?${queryString}`
    : "";

  return requestAdminApi<
    KnowledgeBaseAdmin[]
  >(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/knowledge-bases${query}`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function getAdminKnowledgeBase(
  accessToken: string,
  tenantId: string,
  knowledgeBaseId: string,
): Promise<KnowledgeBaseAdmin> {
  return requestAdminApi<
    KnowledgeBaseAdmin
  >(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/knowledge-bases/${
      encodeURIComponent(knowledgeBaseId)
    }`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function listAdminKnowledgeDocuments(
  accessToken: string,
  tenantId: string,
  knowledgeBaseId: string,
): Promise<KnowledgeDocumentAdmin[]> {
  return requestAdminApi<
    KnowledgeDocumentAdmin[]
  >(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/knowledge-bases/${
      encodeURIComponent(knowledgeBaseId)
    }/documents`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function listAdminKnowledgeIngestionJobs(
  accessToken: string,
  tenantId: string,
  knowledgeBaseId: string,
  limit = 100,
): Promise<KnowledgeIngestionJobAdmin[]> {
  const normalizedLimit = Math.min(
    Math.max(
      Math.trunc(limit),
      1,
    ),
    200,
  );

  return requestAdminApi<
    KnowledgeIngestionJobAdmin[]
  >(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/knowledge-bases/${
      encodeURIComponent(knowledgeBaseId)
    }/ingestion-jobs?limit=${normalizedLimit}`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function permanentlyDeleteAdminAgent(
  accessToken: string,
  tenantId: string,
  agentId: string,
  confirmation: string,
): Promise<void> {
  await requestAdminApi<void>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/agents/${
      encodeURIComponent(agentId)
    }?confirm=${
      encodeURIComponent(confirmation)
    }`,
    {
      method: "DELETE",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function getAdminTenant(
  accessToken: string,
  tenantId: string,
): Promise<TenantAdmin> {
  return requestAdminApi<TenantAdmin>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function revokeAdminApiKey(
  accessToken: string,
  tenantId: string,
  keyId: string,
): Promise<ApiKeyAdmin> {
  return requestAdminApi<ApiKeyAdmin>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/api-keys/${
      encodeURIComponent(keyId)
    }/revoke`,
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function revokeAllAdminApiKeys(
  accessToken: string,
  tenantId: string,
): Promise<RevokeAllApiKeysResult> {
  return requestAdminApi<RevokeAllApiKeysResult>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/api-keys/revoke-all`,
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function updateAdminTenantStatus(
  accessToken: string,
  tenantId: string,
  isActive: boolean,
): Promise<TenantAdmin> {
  return requestAdminApi<TenantAdmin>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/status`,
    {
      method: "PATCH",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify({
        is_active: isActive,
      }),
    },
  );
}

export async function permanentlyDeleteAdminTenant(
  accessToken: string,
  tenantId: string,
  confirmation: string,
): Promise<void> {
  await requestAdminApi<void>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }?confirm=${
      encodeURIComponent(confirmation)
    }`,
    {
      method: "DELETE",
      headers: bearerHeaders(accessToken),
    },
  );
}

export function adminApiErrorResponse(
  error: unknown,
): Response {
  if (error instanceof AdminApiError) {
    const headers = new Headers({
      "Cache-Control": "no-store",
    });

    if (error.retryAfter) {
      headers.set(
        "Retry-After",
        error.retryAfter,
      );
    }

    return Response.json(
      {
        detail: error.detail,
      },
      {
        status: error.status,
        headers,
      },
    );
  }

  if (error instanceof AdminApiUnavailableError) {
    return Response.json(
      {
        detail: "The authentication service is unavailable.",
      },
      {
        status: 502,
        headers: {
          "Cache-Control": "no-store",
        },
      },
    );
  }

  console.error(
    "Unexpected Admin BFF error",
    error,
  );

  return Response.json(
    {
      detail: "An unexpected authentication error occurred.",
    },
    {
      status: 500,
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
