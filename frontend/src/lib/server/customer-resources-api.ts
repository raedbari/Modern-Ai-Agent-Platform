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

  if (
    init.body !== undefined &&
    !headers.has("Content-Type")
  ) {
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
