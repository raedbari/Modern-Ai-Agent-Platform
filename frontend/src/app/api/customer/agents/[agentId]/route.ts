import {
  updateCustomerAgent,
  type CustomerAgentUpdate,
} from "@/lib/server/customer-resources-api";

import {
  tenantApiErrorResponse,
} from "@/lib/server/tenant-auth-api";

import {
  withTenantAccessToken,
} from "@/lib/server/tenant-session";

type RouteContext = {
  params: Promise<{
    agentId: string;
  }>;
};

export const dynamic = "force-dynamic";

export async function PATCH(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    agentId,
  } = await context.params;

  let payload: CustomerAgentUpdate;

  try {
    payload =
      (await request.json()) as CustomerAgentUpdate;
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
          updateCustomerAgent(
            accessToken,
            agentId,
            payload,
          ),
      );

    return Response.json(
      agent,
      {
        status: 200,
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
