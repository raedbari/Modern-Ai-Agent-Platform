import {
  adminApiErrorResponse,
  createAdminKnowledgeBase,
  listAdminKnowledgeBases,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{
    tenantId: string;
  }>;
};

export const dynamic = "force-dynamic";

function validationError(
  detail: string,
): Response {
  return Response.json(
    {
      detail,
    },
    {
      status: 422,
      headers: {
        "Cache-Control":
          "private, no-store, max-age=0",
      },
    },
  );
}

export async function GET(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
  } = await context.params;

  const rawAgentId =
    new URL(request.url)
      .searchParams
      .get("agentId");

  const agentId =
    rawAgentId?.trim() || undefined;

  if (
    agentId !== undefined &&
    agentId.length > 128
  ) {
    return validationError(
      "agentId must contain at most 128 characters.",
    );
  }

  try {
    const items =
      await withAdminAccessToken(
        (accessToken) =>
          listAdminKnowledgeBases(
            accessToken,
            tenantId,
            agentId,
          ),
      );

    return Response.json(
      items,
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

export async function POST(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const { tenantId } = await context.params;

  const payload = await request
    .json()
    .catch(() => null) as {
      name?: unknown;
      description?: unknown;
      status?: unknown;
      assigned_agent_ids?: unknown;
    classification?: unknown;
    } | null;

  const name =
    typeof payload?.name === "string"
      ? payload.name.trim()
      : "";

  if (!name) {
    return validationError(
      "Knowledge base name is required.",
    );
  }

  const assignedAgentIds =
    Array.isArray(payload?.assigned_agent_ids)
      ? payload.assigned_agent_ids.filter(
          (item): item is string =>
            typeof item === "string" &&
            item.trim().length > 0,
        )
      : [];

  try {
    const item = await withAdminAccessToken(
      (accessToken) =>
        createAdminKnowledgeBase(
          accessToken,
          tenantId,
          {
            name,
            description:
              typeof payload?.description === "string"
                ? payload.description
                : "",
            status:
              payload?.status === "inactive"
                ? "inactive"
                : "active",
            classification:
              payload?.classification === "public" ||
              payload?.classification === "restricted"
                ? payload.classification
                : "internal",
            assigned_agent_ids:
              assignedAgentIds,
          },
        ),
    );

    return Response.json(
      item,
      {
        status: 201,
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
