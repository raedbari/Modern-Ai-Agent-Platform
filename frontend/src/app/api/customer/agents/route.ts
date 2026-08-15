import {
  createCustomerAgent,
  type CustomerAgentCreate,
} from "@/lib/server/customer-resources-api";

import {
  tenantApiErrorResponse,
} from "@/lib/server/tenant-auth-api";

import {
  withTenantAccessToken,
} from "@/lib/server/tenant-session";

export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
): Promise<Response> {
  let payload: CustomerAgentCreate;

  try {
    payload =
      (await request.json()) as CustomerAgentCreate;
  } catch {
    return Response.json(
      {
        detail:
          "Invalid JSON payload.",
      },
      {
        status: 400,
        headers: {
          "Cache-Control": "no-store",
        },
      },
    );
  }

  try {
    const agent =
      await withTenantAccessToken(
        (accessToken) =>
          createCustomerAgent(
            accessToken,
            payload,
          ),
      );

    return Response.json(
      agent,
      {
        status: 201,
        headers: {
          "Cache-Control":
            "private, no-store, max-age=0",
        },
      },
    );
  } catch (error) {
    return tenantApiErrorResponse(
      error,
    );
  }
}
