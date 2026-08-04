import {
  adminApiErrorResponse,
  updateAdminAgentStatus,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{
    tenantId: string;
    agentId: string;
  }>;
};

export async function PATCH(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
    agentId,
  } = await context.params;

  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return Response.json(
      {
        detail:
          "Request body must be valid JSON.",
      },
      {
        status: 400,
      },
    );
  }

  if (
    body === null ||
    typeof body !== "object" ||
    Array.isArray(body) ||
    typeof (
      body as {
        is_active?: unknown;
      }
    ).is_active !== "boolean"
  ) {
    return Response.json(
      {
        detail:
          "is_active must be a boolean.",
      },
      {
        status: 422,
      },
    );
  }

  const isActive = (
    body as {
      is_active: boolean;
    }
  ).is_active;

  try {
    const agent =
      await withAdminAccessToken(
        (accessToken) =>
          updateAdminAgentStatus(
            accessToken,
            tenantId,
            agentId,
            isActive,
          ),
      );

    return Response.json(
      agent,
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
