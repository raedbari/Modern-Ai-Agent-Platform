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
