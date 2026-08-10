import {
  updateCustomerKnowledgeBase,
} from "@/lib/server/customer-resources-api";

import {
  tenantApiErrorResponse,
} from "@/lib/server/tenant-auth-api";

import {
  withTenantAccessToken,
} from "@/lib/server/tenant-session";

type RouteContext = {
  params: Promise<{
    knowledgeBaseId: string;
  }>;
};

type UpdatePayload = {
  agentId?: unknown;
  name?: unknown;
  description?: unknown;
};

export const dynamic = "force-dynamic";

export async function PATCH(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    knowledgeBaseId,
  } = await context.params;

  let payload: UpdatePayload;

  try {
    payload =
      (await request.json()) as UpdatePayload;
  } catch {
    return Response.json(
      {
        detail: "Invalid JSON payload.",
      },
      {
        status: 400,
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

  try {
    const knowledgeBase =
      await withTenantAccessToken(
        (accessToken) =>
          updateCustomerKnowledgeBase(
            accessToken,
            agentId,
            knowledgeBaseId,
            {
              ...(name
                ? { name }
                : {}),
              description,
            },
          ),
      );

    return Response.json(
      knowledgeBase,
      {
        status: 200,
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
