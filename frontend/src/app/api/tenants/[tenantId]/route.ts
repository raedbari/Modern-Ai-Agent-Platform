import {
  adminApiErrorResponse,
  permanentlyDeleteAdminTenant,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{
    tenantId: string;
  }>;
};

export async function DELETE(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
  } = await context.params;

  const confirmation =
    new URL(request.url)
      .searchParams
      .get("confirm");

  if (confirmation !== tenantId) {
    return Response.json(
      {
        detail:
          "Confirmation must exactly match tenant_id.",
      },
      {
        status: 422,
      },
    );
  }

  try {
    await withAdminAccessToken(
      (accessToken) =>
        permanentlyDeleteAdminTenant(
          accessToken,
          tenantId,
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
