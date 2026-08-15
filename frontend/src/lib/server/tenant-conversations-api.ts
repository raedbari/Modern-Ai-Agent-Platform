import "server-only";

import { getApiBaseUrl } from "./config";

import {
  TenantApiError,
  TenantApiUnavailableError,
} from "./tenant-auth-api";

export type TenantConversationItem = {
  id: string;
  tenant_id: string;
  agent_id: string;
  agent_name: string;
  user_identifier: string | null;
  metadata: Record<string, unknown> | null;
  message_count: number;
  user_message_count: number;
  assistant_message_count: number;
  last_message_role: string | null;
  last_message_preview: string | null;
  created_at: string;
  updated_at: string;
};

export type TenantConversationListResponse = {
  items: TenantConversationItem[];
  total: number;
  limit: number;
  offset: number;
};

export type TenantMessageItem = {
  id: string;
  tenant_id: string;
  conversation_id: string;
  role: "system" | "user" | "assistant" | "tool";
  content: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
};

export type TenantMessageListResponse = {
  items: TenantMessageItem[];
  total: number;
  limit: number;
  offset: number;
};

type ErrorPayload = {
  detail?: unknown;
};

async function readResponseBody(
  response: Response,
): Promise<unknown> {
  const text = await response.text();

  if (!text) return undefined;

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function requestApi<T>(
  path: string,
  accessToken: string,
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(
      `${getApiBaseUrl()}${path}`,
      {
        method: "GET",
        headers: {
          Accept: "application/json",
          Authorization:
            `Bearer ${accessToken}`,
        },
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

export async function listTenantConversations(
  accessToken: string,
  options: {
    agentId?: string;
    limit?: number;
    offset?: number;
  } = {},
): Promise<TenantConversationListResponse> {
  const params =
    new URLSearchParams();

  if (options.agentId) {
    params.set(
      "agent_id",
      options.agentId,
    );
  }

  params.set(
    "limit",
    String(options.limit ?? 100),
  );

  params.set(
    "offset",
    String(options.offset ?? 0),
  );

  return requestApi<TenantConversationListResponse>(
    `/api/customer/conversations?${params.toString()}`,
    accessToken,
  );
}

export async function getTenantConversation(
  accessToken: string,
  conversationId: string,
): Promise<TenantConversationItem> {
  return requestApi<TenantConversationItem>(
    `/api/customer/conversations/${
      encodeURIComponent(conversationId)
    }`,
    accessToken,
  );
}

export async function listTenantConversationMessages(
  accessToken: string,
  conversationId: string,
  options: {
    limit?: number;
    offset?: number;
  } = {},
): Promise<TenantMessageListResponse> {
  const params =
    new URLSearchParams();

  params.set(
    "limit",
    String(options.limit ?? 200),
  );

  params.set(
    "offset",
    String(options.offset ?? 0),
  );

  return requestApi<TenantMessageListResponse>(
    `/api/customer/conversations/${
      encodeURIComponent(conversationId)
    }/messages?${params.toString()}`,
    accessToken,
  );
}

export function tenantConversationsApiErrorResponse(
  error: unknown,
): Response {
  if (error instanceof TenantApiError) {
    return Response.json(
      {
        detail: error.detail,
      },
      {
        status: error.status,
        headers: {
          "Cache-Control": "no-store",
        },
      },
    );
  }

  if (
    error instanceof
    TenantApiUnavailableError
  ) {
    return Response.json(
      {
        detail:
          "The tenant conversations service is unavailable.",
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
    "Unexpected customer conversations error",
    error,
  );

  return Response.json(
    {
      detail:
        "An unexpected error occurred.",
    },
    {
      status: 500,
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
