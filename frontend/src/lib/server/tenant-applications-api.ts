import "server-only";

import type { ApplicationStatus } from "./tenant-auth-api";

import { getApiBaseUrl } from "./config";

export type { ApplicationStatus };

export type TenantApplication = {
  id: string;
  applicant_name: string;
  email: string;
  company_name: string;
  plan: string;
  email_verified: boolean;
  status: ApplicationStatus;
  submitted_at: string;
  review_notes?: string;
  reviewed_at?: string;
  reviewed_by?: string;
};

type ErrorPayload = {
  detail?: unknown;
};

export class TenantApplicationsApiError extends Error {
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
        : `Tenant Applications API request failed with status ${status}.`,
    );

    this.name = "TenantApplicationsApiError";
    this.status = status;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }
}

export class TenantApplicationsApiUnavailableError extends Error {
  constructor(cause?: unknown) {
    super("The Tenant Applications API is currently unavailable.", {
      cause,
    });

    this.name = "TenantApplicationsApiUnavailableError";
  }
}

function buildUrl(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(
      `Tenant Applications API path must start with "/": ${path}`,
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

async function requestTenantApplicationsApi<T>(
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
    throw new TenantApplicationsApiUnavailableError(error);
  }

  const body = await readResponseBody(response);

  if (!response.ok) {
    const payload =
      body !== null &&
      typeof body === "object"
        ? body as ErrorPayload
        : undefined;

    throw new TenantApplicationsApiError(
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

export async function listTenantApplications(
  accessToken: string,
): Promise<TenantApplication[]> {
  return requestTenantApplicationsApi<TenantApplication[]>(
    "/api/admin/tenant-applications/",
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function getTenantApplication(
  accessToken: string,
  id: string,
): Promise<TenantApplication> {
  return requestTenantApplicationsApi<TenantApplication>(
    `/api/admin/tenant-applications/${encodeURIComponent(id)}`,
    {
      method: "GET",
      headers: bearerHeaders(accessToken),
    },
  );
}

export async function approveTenantApplication(
  accessToken: string,
  id: string,
): Promise<TenantApplication> {
  return requestTenantApplicationsApi(
    `/api/admin/tenant-applications/${encodeURIComponent(id)}/approve`,
    {
      method: "POST",
      headers: {
        ...bearerHeaders(accessToken),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    },
  );
}

export async function rejectTenantApplication(
  accessToken: string,
  id: string,
  reason?: string,
): Promise<TenantApplication> {
  return requestTenantApplicationsApi<TenantApplication>(
    `/api/admin/tenant-applications/${encodeURIComponent(id)}/reject`,
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify({ reason }),
    },
  );
}

export async function requestApplicationChanges(
  accessToken: string,
  id: string,
  notes: string,
): Promise<TenantApplication> {
  return requestTenantApplicationsApi<TenantApplication>(
    `/api/admin/tenant-applications/${encodeURIComponent(id)}/request-changes`,
    {
      method: "POST",
      headers: bearerHeaders(accessToken),
      body: JSON.stringify({ notes }),
    },
  );
}

export function tenantApplicationsApiErrorResponse(
  error: unknown,
): Response {
  if (error instanceof TenantApplicationsApiError) {
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

  if (error instanceof TenantApplicationsApiUnavailableError) {
    return Response.json(
      {
        detail: "The tenant applications service is unavailable.",
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
    "Unexpected Tenant Applications BFF error",
    error,
  );

  return Response.json(
    {
      detail: "An unexpected error occurred.",
    },
    {
      status: 500,
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
