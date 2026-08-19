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

export type EvaluationDatasetSummary =
  components["schemas"]["EvaluationDatasetSummaryResponse"];

export type EvaluationDataset =
  components["schemas"]["EvaluationDataset"];

export type EvaluationRun =
  components["schemas"]["EvaluationRunResponse"];

export type EvaluationRunCreatePayload =
  components["schemas"]["EvaluationRunCreateRequest"];


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

  const isFormDataBody =
    typeof FormData !== "undefined" &&
    init.body instanceof FormData;

  if (
    init.body !== undefined &&
    !isFormDataBody &&
    !headers.has("Content-Type")
  ) {
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
  components["schemas"]["backend__app__api__schemas__widget__WidgetSettingsResponse"];

export type WidgetSettingsUpdatePayload =
  components["schemas"]["WidgetSettingsUpdate"];

export type KnowledgeBaseAdmin =
  components["schemas"]["KnowledgeBaseAdminResponse"];

export type KnowledgeDocumentAdmin =
  components["schemas"]["DocumentAdminResponse"];

export type KnowledgeIngestionJobAdmin =
  components["schemas"]["IngestionJobAdminResponse"];

export type TenantAdminCreatePayload = {
  name: string;
  is_active?: boolean;
};

export type AgentAdminCreatePayload = {
  name: string;
  system_prompt?: string | null;
  knowledge_mode?: "required" | "preferred" | "disabled";
  contact_message?: string | null;
};

export type KnowledgeBaseAdminCreatePayload =
  components["schemas"]["KnowledgeBaseAdminCreate"];

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

export async function listAdminEvaluationDatasets(
  accessToken: string,
): Promise<EvaluationDatasetSummary[]> {
  return requestAdminApi<EvaluationDatasetSummary[]>(
    "/api/admin/evaluation/datasets",
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function getAdminEvaluationDataset(
  accessToken: string,
  name: string,
  version: string,
): Promise<EvaluationDataset> {
  return requestAdminApi<EvaluationDataset>(
    `/api/admin/evaluation/datasets/${
      encodeURIComponent(name)
    }/${encodeURIComponent(version)}`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function listAdminEvaluationRuns(
  accessToken: string,
): Promise<EvaluationRun[]> {
  return requestAdminApi<EvaluationRun[]>(
    "/api/admin/evaluation/runs",
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function createAdminEvaluationRun(
  accessToken: string,
  payload: EvaluationRunCreatePayload,
): Promise<EvaluationRun> {
  return requestAdminApi<EvaluationRun>(
    "/api/admin/evaluation/runs",
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify(payload),
    },
  );
}

export async function getAdminEvaluationRun(
  accessToken: string,
  runId: string,
): Promise<EvaluationRun> {
  return requestAdminApi<EvaluationRun>(
    `/api/admin/evaluation/runs/${
      encodeURIComponent(runId)
    }`,
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

export async function createAdminTenant(
  accessToken: string,
  payload: TenantAdminCreatePayload,
): Promise<TenantAdmin> {
  return requestAdminApi<TenantAdmin>(
    "/api/admin/tenants",
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify(payload),
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

export async function createAdminAgent(
  accessToken: string,
  tenantId: string,
  payload: AgentAdminCreatePayload,
): Promise<AgentAdmin> {
  return requestAdminApi<AgentAdmin>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/agents`,
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify(payload),
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



export async function createAdminKnowledgeBase(
  accessToken: string,
  tenantId: string,
  payload: KnowledgeBaseAdminCreatePayload,
): Promise<KnowledgeBaseAdmin> {
  return requestAdminApi<KnowledgeBaseAdmin>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/knowledge-bases`,
    {
      method: "POST",
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

export async function replaceAdminKnowledgeBaseAgents(
  accessToken: string,
  tenantId: string,
  knowledgeBaseId: string,
  agentIds: string[],
): Promise<KnowledgeBaseAdmin> {
  return requestAdminApi<KnowledgeBaseAdmin>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/knowledge-bases/${
      encodeURIComponent(knowledgeBaseId)
    }/agents`,
    {
      method: "PUT",
      headers: {
        ...bearerHeaders(accessToken),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        agent_ids: agentIds,
      }),
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

export type ConversationAdmin =
  components["schemas"]["ConversationAdminResponse"];

export type ConversationAdminList =
  components["schemas"]["ConversationAdminListResponse"];

export type MessageAdmin =
  components["schemas"]["MessageAdminResponse"];

export type MessageAdminList =
  components["schemas"]["MessageAdminListResponse"];

type ConversationListOptions = {
  agentId?: string;
  limit?: number;
  offset?: number;
};

type MessageListOptions = {
  limit?: number;
  offset?: number;
};

function normalizeInteger(
  value: number | undefined,
  fallback: number,
  minimum: number,
  maximum: number,
): number {
  if (
    value === undefined ||
    !Number.isFinite(value)
  ) {
    return fallback;
  }

  return Math.min(
    Math.max(
      Math.trunc(value),
      minimum,
    ),
    maximum,
  );
}

export async function listAdminConversations(
  accessToken: string,
  tenantId: string,
  options: ConversationListOptions = {},
): Promise<ConversationAdminList> {
  const searchParams =
    new URLSearchParams();

  const normalizedAgentId =
    options.agentId?.trim();

  if (normalizedAgentId) {
    searchParams.set(
      "agent_id",
      normalizedAgentId,
    );
  }

  searchParams.set(
    "limit",
    String(
      normalizeInteger(
        options.limit,
        100,
        1,
        200,
      ),
    ),
  );

  searchParams.set(
    "offset",
    String(
      normalizeInteger(
        options.offset,
        0,
        0,
        Number.MAX_SAFE_INTEGER,
      ),
    ),
  );

  return requestAdminApi<
    ConversationAdminList
  >(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/conversations?${searchParams.toString()}`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function getAdminConversation(
  accessToken: string,
  tenantId: string,
  conversationId: string,
): Promise<ConversationAdmin> {
  return requestAdminApi<
    ConversationAdmin
  >(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/conversations/${
      encodeURIComponent(conversationId)
    }`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function listAdminConversationMessages(
  accessToken: string,
  tenantId: string,
  conversationId: string,
  options: MessageListOptions = {},
): Promise<MessageAdminList> {
  const searchParams =
    new URLSearchParams();

  searchParams.set(
    "limit",
    String(
      normalizeInteger(
        options.limit,
        200,
        1,
        500,
      ),
    ),
  );

  searchParams.set(
    "offset",
    String(
      normalizeInteger(
        options.offset,
        0,
        0,
        Number.MAX_SAFE_INTEGER,
      ),
    ),
  );

  return requestAdminApi<
    MessageAdminList
  >(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/conversations/${
      encodeURIComponent(conversationId)
    }/messages?${searchParams.toString()}`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function queueAdminKnowledgeDocument(
  accessToken: string,
  tenantId: string,
  knowledgeBaseId: string,
  formData: FormData,
): Promise<
  components["schemas"]["DocumentJobAdminResponse"]
> {
  return requestAdminApi<
    components["schemas"]["DocumentJobAdminResponse"]
  >(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/knowledge-bases/${
      encodeURIComponent(knowledgeBaseId)
    }/documents`,
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
      body: formData,
    },
  );
}

export async function queueAdminKnowledgeDocumentReplacement(
  accessToken: string,
  tenantId: string,
  knowledgeBaseId: string,
  documentId: string,
  formData: FormData,
): Promise<
  components["schemas"]["DocumentJobAdminResponse"]
> {
  return requestAdminApi<
    components["schemas"]["DocumentJobAdminResponse"]
  >(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/knowledge-bases/${
      encodeURIComponent(knowledgeBaseId)
    }/documents/${
      encodeURIComponent(documentId)
    }/replace`,
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
      body: formData,
    },
  );
}


export type WidgetConnectorType =
  | "wordpress"
  | "react_next"
  | "managed"
  | "custom";

export type WidgetConnectorPairingCreated = {
  pairing_id: string;
  pairing_code: string;
  origin: string;
  connector_type: WidgetConnectorType;
  expires_at: string;
  expires_in: number;
};

export async function createAdminWidgetConnectorPairing(
  accessToken: string,
  tenantId: string,
  agentId: string,
  payload: {
    origin: string;
    connector_type: WidgetConnectorType;
  },
): Promise<WidgetConnectorPairingCreated> {
  return requestAdminApi<WidgetConnectorPairingCreated>(
    `/api/admin/tenants/${
      encodeURIComponent(tenantId)
    }/agents/${
      encodeURIComponent(agentId)
    }/widget/pairings`,
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify(payload),
    },
  );
}
