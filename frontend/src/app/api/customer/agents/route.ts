import {
  createCustomerAgent,
  listCustomerAgents,
  type CustomerAgentCreate,
} from "@/lib/server/customer-resources-api";

import {
  tenantApiErrorResponse,
} from "@/lib/server/tenant-auth-api";

import {
  withTenantAccessToken,
} from "@/lib/server/tenant-session";

function browserSafeAgent<T extends { tenant_id: string }>(agent: T): Omit<T, "tenant_id"> {
  const safe: Partial<T> = { ...agent };
  delete safe.tenant_id;
  return safe as Omit<T, "tenant_id">;
}

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  try {
    const agents = await withTenantAccessToken(listCustomerAgents);
    return Response.json(agents.map(browserSafeAgent), { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    return tenantApiErrorResponse(error);
  }
}

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
      browserSafeAgent(agent),
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
