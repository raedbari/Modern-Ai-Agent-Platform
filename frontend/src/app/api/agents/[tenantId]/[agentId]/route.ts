import {
  adminApiErrorResponse,
  permanentlyDeleteAdminAgent,
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

export async function DELETE(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
    agentId,
  } = await context.params;

  const confirmation =
    new URL(request.url)
      .searchParams
      .get("confirm");

  if (confirmation !== agentId) {
    return Response.json(
      {
        detail:
          "Confirmation must exactly match agent_id.",
      },
      {
        status: 422,
      },
    );
  }

  try {
    await withAdminAccessToken(
      (accessToken) =>
        permanentlyDeleteAdminAgent(
          accessToken,
          tenantId,
          agentId,
          confirmation,
        ),
    );

    return new Response(null, {
      status: 204,
      headers: {
        "Cache-Control":
          "private, no-store, max-age=0",
      },
    });
  } catch (error) {
    return adminApiErrorResponse(error);
  }
}
