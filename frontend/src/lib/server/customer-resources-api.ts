import "server-only";

import { getApiBaseUrl } from "./config";

import {
  TenantApiError,
  TenantApiUnavailableError,
} from "./tenant-auth-api";

export type CustomerAgent = {
  id: string;
  tenant_id: string;
  name: string;
  is_active: boolean;
  knowledge_mode: string;
  system_prompt: string | null;
  contact_message: string | null;
  created_at: string;
  updated_at: string;
};

export type CustomerAgentCreate = {
  name: string;
  system_prompt?: string | null;
  knowledge_mode?: "required" | "preferred" | "disabled";
  contact_message?: string | null;
};

export type CustomerAgentUpdate = {
  name?: string;
  system_prompt?: string | null;
  knowledge_mode?: "required" | "preferred" | "disabled";
  contact_message?: string | null;
};


export type CustomerKnowledgeBase = {
  id: string;
  name: string;
  description: string;
  status: string;
  classification: "public" | "internal" | "restricted";
};

export type CustomerKnowledgeBaseCreate = {
  name: string;
  description?: string;
  classification?: "public" | "internal" | "restricted";
};

export type CustomerKnowledgeBaseUpdate = {
  name?: string;
  description?: string;
  status?: "active" | "inactive";
  classification?: "public" | "internal" | "restricted";
};

export type CustomerDocument = {
  id: string;
  knowledge_base_id: string;
  original_filename: string;
  source_name: string;
  mime_type: string;
  file_size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed" | "archived";
  failure_reason: string | null;
  version_number: number;
  version_family_id: string;
  predecessor_id: string | null;
  superseded_by_id: string | null;
  created_at: string;
  updated_at: string;
};

export type CustomerDocumentJob = {
  job_id: string | null;
  document: CustomerDocument;
  status: "pending" | "processing" | "succeeded" | "failed" | "duplicate";
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  duplicate: boolean;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
};

export type CustomerChatResponse = {
  conversation_id: string;
  message_id: string;
  reply: string;
  answer_status: "grounded" | "generated" | "insufficient_knowledge" | "temporarily_unavailable";
  sources: Array<{
    citation_id: string;
    source_name: string;
    document_id: string;
    page_number: number;
    similarity_score: number;
  }>;
};

export type CustomerWidgetSettings = {
  tenant_id: string;
  agent_id: string;
  public_widget_id: string;
  is_enabled: boolean;
  display_name: string | null;
  greeting: string | null;
  primary_color: string;
  text_color: string;
  launcher_color: string;
  header_color: string;
  user_message_color: string;
  position: "left" | "right";
  appearance: "light" | "dark";
  allowed_origins: string[];
};

export type CustomerWidgetPreview = {
  session_token: string;
  token_type: "Bearer";
  expires_in: number;
  session_id: string;
  widget: {
    widget_id: string;
    display_name: string;
    greeting: string | null;
    theme: Record<string, string>;
  };
};

export type CustomerWidgetInstallation = {
  pairing_id: string | null;
  status: "pending" | "verified" | "expired" | "failed";
  origin: string | null;
  expires_at: string | null;
  connected_at: string | null;
  error_code: string | null;
  detail: string;
  checks: {
    script_loaded: boolean;
    origin_valid: boolean;
    public_config_loaded: boolean;
    bootstrap_succeeded: boolean;
  };
};

type ErrorPayload = {
  detail?: unknown;
};

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

async function requestCustomerResource<T>(
  path: string,
  accessToken: string,
  init: RequestInit,
): Promise<T> {
  const headers = new Headers(
    init.headers,
  );

  headers.set(
    "Accept",
    "application/json",
  );

  headers.set(
    "Authorization",
    `Bearer ${accessToken}`,
  );

  if (init.body !== undefined && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set(
      "Content-Type",
      "application/json",
    );
  }

  let response: Response;

  try {
    response = await fetch(
      `${getApiBaseUrl()}${path}`,
      {
        ...init,
        headers,
        cache: "no-store",
      },
    );
  } catch (error) {
    throw new TenantApiUnavailableError(
      error,
    );
  }

  const body =
    await readResponseBody(response);

  if (!response.ok) {
    const payload =
      body !== null &&
      typeof body === "object"
        ? body as ErrorPayload
        : undefined;

    throw new TenantApiError(
      response.status,
      payload?.detail ??
        body ??
        response.statusText,
      response.headers.get(
        "retry-after",
      ),
    );
  }

  return body as T;
}

export async function createCustomerAgent(
  accessToken: string,
  payload: CustomerAgentCreate,
): Promise<CustomerAgent> {
  return requestCustomerResource<CustomerAgent>(
    "/api/customer/agents",
    accessToken,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function listCustomerAgents(accessToken: string): Promise<CustomerAgent[]> {
  return requestCustomerResource<CustomerAgent[]>("/api/customer/agents", accessToken, { method: "GET" });
}

export async function getCustomerAgent(accessToken: string, agentId: string): Promise<CustomerAgent> {
  return requestCustomerResource<CustomerAgent>(`/api/customer/agents/${encodeURIComponent(agentId)}`, accessToken, { method: "GET" });
}

export async function deleteCustomerAgent(accessToken: string, agentId: string): Promise<void> {
  await requestCustomerResource<void>(`/api/customer/agents/${encodeURIComponent(agentId)}`, accessToken, { method: "DELETE" });
}

export async function updateCustomerAgent(
  accessToken: string,
  agentId: string,
  payload: CustomerAgentUpdate,
): Promise<CustomerAgent> {
  return requestCustomerResource<CustomerAgent>(
    `/api/customer/agents/${
      encodeURIComponent(agentId)
    }`,
    accessToken,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
}

export async function createCustomerKnowledgeBase(
  accessToken: string,
  agentId: string,
  payload: CustomerKnowledgeBaseCreate,
): Promise<CustomerKnowledgeBase> {
  return requestCustomerResource<CustomerKnowledgeBase>(
    "/api/knowledge-bases",
    accessToken,
    {
      method: "POST",
      headers: {
        "X-Agent-ID": agentId,
      },
      body: JSON.stringify(payload),
    },
  );
}

export async function listCustomerKnowledgeBases(accessToken: string): Promise<CustomerKnowledgeBase[]> {
  return requestCustomerResource<CustomerKnowledgeBase[]>("/api/customer/knowledge-bases", accessToken, { method: "GET" });
}

export async function assignCustomerKnowledgeBase(
  accessToken: string,
  agentId: string,
  knowledgeBaseId: string,
): Promise<CustomerKnowledgeBase> {
  return requestCustomerResource<CustomerKnowledgeBase>(
    `/api/customer/agents/${encodeURIComponent(agentId)}/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}`,
    accessToken,
    { method: "PUT" },
  );
}

function knowledgeHeaders(agentId: string): HeadersInit {
  return { "X-Agent-ID": agentId };
}

export async function listCustomerDocuments(accessToken: string, agentId: string, knowledgeBaseId: string): Promise<CustomerDocument[]> {
  return requestCustomerResource<CustomerDocument[]>(`/api/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents`, accessToken, { method: "GET", headers: knowledgeHeaders(agentId) });
}

export async function queueCustomerDocument(accessToken: string, agentId: string, knowledgeBaseId: string, form: FormData): Promise<CustomerDocumentJob> {
  return requestCustomerResource<CustomerDocumentJob>(`/api/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/document-jobs`, accessToken, { method: "POST", headers: knowledgeHeaders(agentId), body: form });
}

export async function getCustomerDocumentJob(accessToken: string, agentId: string, knowledgeBaseId: string, jobId: string): Promise<CustomerDocumentJob> {
  return requestCustomerResource<CustomerDocumentJob>(`/api/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/document-jobs/${encodeURIComponent(jobId)}`, accessToken, { method: "GET", headers: knowledgeHeaders(agentId) });
}

export async function mutateCustomerDocument(accessToken: string, agentId: string, knowledgeBaseId: string, documentId: string, action: "delete" | "archive", form?: FormData): Promise<CustomerDocument | void> {
  const suffix = action === "archive" ? "/archive" : "";
  return requestCustomerResource<CustomerDocument | void>(`/api/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents/${encodeURIComponent(documentId)}${suffix}`, accessToken, { method: action === "delete" ? "DELETE" : "POST", headers: knowledgeHeaders(agentId), body: form });
}

export async function replaceCustomerDocument(accessToken: string, agentId: string, knowledgeBaseId: string, documentId: string, form: FormData): Promise<CustomerDocument> {
  return requestCustomerResource<CustomerDocument>(`/api/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents/${encodeURIComponent(documentId)}/reindex`, accessToken, { method: "POST", headers: knowledgeHeaders(agentId), body: form });
}

export async function testCustomerChat(accessToken: string, agentId: string, payload: { message: string; conversation_id?: string }): Promise<CustomerChatResponse> {
  return requestCustomerResource<CustomerChatResponse>("/api/chat", accessToken, { method: "POST", headers: knowledgeHeaders(agentId), body: JSON.stringify(payload) });
}

export async function getCustomerWidgetSettings(accessToken: string, agentId: string): Promise<CustomerWidgetSettings> {
  return requestCustomerResource<CustomerWidgetSettings>(`/api/customer/agents/${encodeURIComponent(agentId)}/widget-settings`, accessToken, { method: "GET" });
}

export async function putCustomerWidgetSettings(accessToken: string, agentId: string, payload: Partial<CustomerWidgetSettings>): Promise<CustomerWidgetSettings> {
  return requestCustomerResource<CustomerWidgetSettings>(`/api/customer/agents/${encodeURIComponent(agentId)}/widget-settings`, accessToken, { method: "PUT", body: JSON.stringify(payload) });
}

export async function bootstrapCustomerWidgetPreview(accessToken: string, agentId: string, origin: string): Promise<CustomerWidgetPreview> {
  return requestCustomerResource<CustomerWidgetPreview>(`/api/customer/agents/${encodeURIComponent(agentId)}/widget-settings/preview/bootstrap`, accessToken, { method: "POST", headers: { Origin: origin } });
}

export async function createCustomerWidgetPairing(accessToken: string, agentId: string, payload: { origin: string; connector_type: "wordpress" | "react_next" | "managed" | "custom" }): Promise<{ pairing_id: string; pairing_code: string; expires_at: string; expires_in: number; origin: string }> {
  return requestCustomerResource(`/api/customer/agents/${encodeURIComponent(agentId)}/widget-settings/pairings`, accessToken, { method: "POST", body: JSON.stringify(payload) });
}

export async function getCustomerWidgetInstallation(
  accessToken: string,
  agentId: string,
  options: { pairingId?: string; origin?: string } = {},
): Promise<CustomerWidgetInstallation> {
  const query = new URLSearchParams();
  if (options.pairingId) query.set("pairing_id", options.pairingId);
  if (options.origin) query.set("origin", options.origin);
  const suffix = query.size > 0 ? `?${query.toString()}` : "";
  return requestCustomerResource<CustomerWidgetInstallation>(
    `/api/customer/agents/${encodeURIComponent(agentId)}/widget-settings/installation${suffix}`,
    accessToken,
    { method: "GET" },
  );
}

export async function deleteCustomerKnowledgeBase(
  accessToken: string,
  agentId: string,
  knowledgeBaseId: string,
): Promise<void> {
  await requestCustomerResource<void>(
    `/api/knowledge-bases/${
      encodeURIComponent(knowledgeBaseId)
    }`,
    accessToken,
    {
      method: "DELETE",
      headers: {
        "X-Agent-ID": agentId,
      },
    },
  );
}

export async function updateCustomerKnowledgeBase(
  accessToken: string,
  agentId: string,
  knowledgeBaseId: string,
  payload: CustomerKnowledgeBaseUpdate,
): Promise<CustomerKnowledgeBase> {
  return requestCustomerResource<CustomerKnowledgeBase>(
    `/api/knowledge-bases/${
      encodeURIComponent(knowledgeBaseId)
    }`,
    accessToken,
    {
      method: "PATCH",
      headers: {
        "X-Agent-ID": agentId,
      },
      body: JSON.stringify(payload),
    },
  );
}
