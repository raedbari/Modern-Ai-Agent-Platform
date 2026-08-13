import {
  adminApiErrorResponse,
  replaceAdminKnowledgeBaseAgents,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{
    tenantId: string;
    knowledgeBaseId: string;
  }>;
};

type UpdatePayload = {
  agent_ids?: unknown;
};

export const dynamic = "force-dynamic";

export async function PUT(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
    knowledgeBaseId,
  } = await context.params;

  const payload = (
    await request
      .json()
      .catch(() => null)
  ) as UpdatePayload | null;

  if (
    payload === null ||
    !Array.isArray(payload.agent_ids) ||
    !payload.agent_ids.every(
      (item) =>
        typeof item === "string" &&
        item.trim().length > 0,
    )
  ) {
    return Response.json(
      {
        detail:
          "agent_ids must be an array of non-empty strings.",
      },
      {
        status: 422,
      },
    );
  }

  try {
    const item =
      await withAdminAccessToken(
        (accessToken) =>
          replaceAdminKnowledgeBaseAgents(
            accessToken,
            tenantId,
            knowledgeBaseId,
            payload.agent_ids as string[],
          ),
      );

    return Response.json(
      item,
      {
        headers: {
          "Cache-Control":
            "private, no-store, max-age=0",
        },
      },
    );
  } catch (error) {
    return adminApiErrorResponse(error);
  }
}
