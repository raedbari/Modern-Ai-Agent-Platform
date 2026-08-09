import "server-only";

import { getApiBaseUrl } from "./config";

export type ApplicationStatus =
  | "email_pending"
  | "under_review"
  | "changes_requested"
  | "approved"
  | "rejected";

export type TenantLoginRequest = {
  email: string;
  password: string;
};

export type TenantLoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
  expires_in: number;
  user_id: string;
  tenant_id: string | null;
  role: string | null;
};

type TenantApplicationProfile = {
  application_id: string;
  company_name: string;
  status: ApplicationStatus;
  submitted_at: string;
  review_note?: string | null;
};

type TenantMembershipProfile = {
  tenant_id: string;
  tenant_name: string;
  membership_id: string;
  role: string;
  status: string;
  created_at: string;
};

type BackendTenantProfile = {
  user_id: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  email_verified_at: string | null;
  created_at: string;
  last_login_at: string | null;
  application: TenantApplicationProfile | null;
  membership: TenantMembershipProfile | null;
};

export type TenantProfile = {
  id: string;
  email: string;
  company_name: string;
  application_status: ApplicationStatus;
  review_notes?: string;
  submitted_at?: string;
  tenant_id: string | null;
  role: string | null;
};

type ErrorPayload = {
  detail?: unknown;
};

export class TenantApiError extends Error {
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
        : `Tenant API request failed with status ${status}.`,
    );

    this.name = "TenantApiError";
    this.status = status;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }
}

export class TenantApiUnavailableError extends Error {
  constructor(cause?: unknown) {
    super("The Tenant API is currently unavailable.", {
      cause,
    });

    this.name = "TenantApiUnavailableError";
  }
}

function buildUrl(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(
      `Tenant API path must start with "/": ${path}`,
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

async function requestTenantApi<T>(
  path: string,
  init: RequestInit,
): Promise<T> {
  const headers = new Headers(init.headers);

  headers.set("Accept", "application/json");

  if (
    init.body !== undefined &&
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
    throw new TenantApiUnavailableError(error);
  }

  const body = await readResponseBody(response);

  if (!response.ok) {
    const payload =
      body !== null &&
      typeof body === "object"
        ? body as ErrorPayload
        : undefined;

    throw new TenantApiError(
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

export async function loginTenant(
  payload: TenantLoginRequest,
): Promise<TenantLoginResponse> {
  return requestTenantApi<TenantLoginResponse>(
    "/api/v1/tenant-auth/login",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function refreshTenantTokens(
  refreshToken: string,
): Promise<TenantLoginResponse> {
  return requestTenantApi<TenantLoginResponse>(
    "/api/v1/tenant-auth/refresh",
    {
      method: "POST",
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    },
  );
}

export async function getTenantProfile(
  accessToken: string,
): Promise<TenantProfile> {
  const raw = await requestTenantApi<BackendTenantProfile>(
    "/api/v1/tenant-auth/me",
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );

  const applicationStatus: ApplicationStatus =
    raw.application?.status ??
    (raw.membership ? "approved" : "under_review");

  return {
    id: raw.user_id,
    email: raw.email,
    company_name:
      raw.application?.company_name ??
      raw.membership?.tenant_name ??
      "",
    application_status: applicationStatus,
    review_notes:
      raw.application?.review_note ?? undefined,
    submitted_at:
      raw.application?.submitted_at ?? undefined,
    tenant_id:
      raw.membership?.tenant_id ?? null,
    role:
      raw.membership?.role ?? null,
  };
}

export async function logoutTenant(
  accessToken: string,
  refreshToken: string,
): Promise<{ detail: string }> {
  return requestTenantApi<{ detail: string }>(
    "/api/v1/tenant-auth/logout",
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    },
  );
}

export function tenantApiErrorResponse(
  error: unknown,
): Response {
  if (error instanceof TenantApiError) {
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

  if (error instanceof TenantApiUnavailableError) {
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
    "Unexpected Tenant BFF error",
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
