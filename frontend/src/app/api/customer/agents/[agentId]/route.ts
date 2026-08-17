import {
  deleteCustomerAgent,
  getCustomerAgent,
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

function browserSafeAgent<T extends { tenant_id: string }>(agent: T): Omit<T, "tenant_id"> {
  const safe: Partial<T> = { ...agent };
  delete safe.tenant_id;
  return safe as Omit<T, "tenant_id">;
}

export async function GET(_request: Request, context: RouteContext): Promise<Response> {
  const { agentId } = await context.params;
  try {
    const agent = await withTenantAccessToken((token) => getCustomerAgent(token, agentId));
    return Response.json(browserSafeAgent(agent), { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    return tenantApiErrorResponse(error);
  }
}

export async function DELETE(_request: Request, context: RouteContext): Promise<Response> {
  const { agentId } = await context.params;
  try {
    await withTenantAccessToken((token) => deleteCustomerAgent(token, agentId));
    return new Response(null, { status: 204, headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    return tenantApiErrorResponse(error);
  }
}

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
      browserSafeAgent(agent),
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
