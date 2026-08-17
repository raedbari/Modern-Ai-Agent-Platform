import {
  createCustomerKnowledgeBase,
  listCustomerKnowledgeBases,
} from "@/lib/server/customer-resources-api";

import {
  tenantApiErrorResponse,
} from "@/lib/server/tenant-auth-api";

import {
  withTenantAccessToken,
} from "@/lib/server/tenant-session";

type CreatePayload = {
  agentId?: unknown;
  name?: unknown;
  description?: unknown;
};

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  try {
    const items = await withTenantAccessToken(listCustomerKnowledgeBases);
    return Response.json(items, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    return tenantApiErrorResponse(error);
  }
}

export async function POST(
  request: Request,
): Promise<Response> {
  let payload: CreatePayload;

  try {
    payload =
      (await request.json()) as CreatePayload;
  } catch {
    return Response.json(
      {
        detail: "Invalid JSON payload.",
      },
      {
        status: 400,
        headers: {
          "Cache-Control": "no-store",
        },
      },
    );
  }

  const agentId =
    typeof payload.agentId === "string"
      ? payload.agentId.trim()
      : "";

  const name =
    typeof payload.name === "string"
      ? payload.name.trim()
      : "";

  const description =
    typeof payload.description === "string"
      ? payload.description.trim()
      : "";

  if (!agentId) {
    return Response.json(
      {
        detail: "Agent ID is required.",
      },
      {
        status: 400,
      },
    );
  }

  if (name.length < 2) {
    return Response.json(
      {
        detail:
          "Knowledge base name is required.",
      },
      {
        status: 400,
      },
    );
  }

  try {
    const knowledgeBase =
      await withTenantAccessToken(
        (accessToken) =>
          createCustomerKnowledgeBase(
            accessToken,
            agentId,
            {
              name,
              description,
            },
          ),
      );

    return Response.json(
      knowledgeBase,
      {
        status: 201,
        headers: {
          "Cache-Control":
            "private, no-store, max-age=0",
        },
      },
    );
  } catch (error) {
    return tenantApiErrorResponse(error);
  }
}
