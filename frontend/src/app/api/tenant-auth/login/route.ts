import {
  getTenantProfile,
  loginTenant,
  tenantApiErrorResponse,
  type TenantLoginRequest,
} from "@/lib/server/tenant-auth-api";

import {
  clearTenantSessionCookies,
  writeTenantSessionCookies,
} from "@/lib/server/tenant-session";

export async function POST(
  request: Request,
): Promise<Response> {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return Response.json(
      {
        detail: "Request body must be valid JSON.",
      },
      {
        status: 400,
      },
    );
  }

  if (
    body === null ||
    typeof body !== "object"
  ) {
    return Response.json(
      {
        detail: "Email and password are required.",
      },
      {
        status: 422,
      },
    );
  }

  const {
    email,
    password,
  } = body as Partial<TenantLoginRequest>;

  if (
    typeof email !== "string" ||
    email.trim().length === 0 ||
    typeof password !== "string" ||
    password.length === 0
  ) {
    return Response.json(
      {
        detail: "Email and password are required.",
      },
      {
        status: 422,
      },
    );
  }

  try {
    const tokens = await loginTenant({
      email: email.trim(),
      password,
    });

    await writeTenantSessionCookies(tokens);

    try {
      const profile = await getTenantProfile(
        tokens.access_token,
      );

      return Response.json(
        {
          expires_in: tokens.expires_in,
          application_status:
            profile.application_status,
        },
        {
          headers: {
            "Cache-Control": "no-store",
          },
        },
      );
    } catch (error) {
      await clearTenantSessionCookies();
      throw error;
    }
  } catch (error) {
    return tenantApiErrorResponse(error);
  }
}
