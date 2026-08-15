import "server-only";

import { getApiBaseUrl } from "./config";
import {
  getTenantProfile,
  type ApplicationStatus,
} from "./tenant-auth-api";

export type SignupRequest = {
  name: string;
  email: string;
  company_name: string;
  password: string;
  requested_plan: string;
  legal_accepted: true;
};

export type SignupResponse = {
  status: ApplicationStatus;
  verification_token?: string | null;
};

export type VerifyEmailRequest = {
  token: string;
};

export type VerifyEmailResponse = {
  email_verified: boolean;
  status: ApplicationStatus;
};

export type ApplicationStatusResponse = {
  status: ApplicationStatus;
  review_notes?: string;
  submitted_at: string;
};

type ErrorPayload = {
  detail?: unknown;
};

export class SaasApiError extends Error {
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
        : `SaaS API request failed with status ${status}.`,
    );

    this.name = "SaasApiError";
    this.status = status;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }
}

export class SaasApiUnavailableError extends Error {
  constructor(cause?: unknown) {
    super("The SaaS API is currently unavailable.", {
      cause,
    });

    this.name = "SaasApiUnavailableError";
  }
}

function buildUrl(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(
      `SaaS API path must start with "/": ${path}`,
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

async function requestSaasApi<T>(
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
    throw new SaasApiUnavailableError(error);
  }

  const body = await readResponseBody(response);

  if (!response.ok) {
    const payload =
      body !== null &&
      typeof body === "object"
        ? (body as ErrorPayload)
        : undefined;

    throw new SaasApiError(
      response.status,
      payload?.detail ?? body ?? response.statusText,
      response.headers.get("retry-after"),
    );
  }

  return body as T;
}

export async function submitSignup(
  payload: SignupRequest,
): Promise<SignupResponse> {
  return requestSaasApi<SignupResponse>(
    "/api/saas/signup",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function verifyEmail(
  payload: VerifyEmailRequest,
): Promise<VerifyEmailResponse> {
  return requestSaasApi<VerifyEmailResponse>(
    "/api/saas/verify-email",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function getApplicationStatus(
  accessToken: string,
): Promise<ApplicationStatusResponse> {
  const profile = await getTenantProfile(accessToken);

  return {
    status: profile.application_status,
    review_notes: profile.review_notes,
    submitted_at: profile.submitted_at ?? "",
  };
}

export function saasApiErrorResponse(
  error: unknown,
): Response {
  if (error instanceof SaasApiError) {
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

  if (error instanceof SaasApiUnavailableError) {
    return Response.json(
      {
        detail: "The SaaS service is unavailable.",
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
    "Unexpected SaaS BFF error",
    error,
  );

  return Response.json(
    {
      detail: "An unexpected SaaS error occurred.",
    },
    {
      status: 500,
      headers: {
        "Cache-Control": "no-store",
      },
    },
  );
}
