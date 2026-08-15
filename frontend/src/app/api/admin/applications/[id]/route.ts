import {
  getTenantApplication,
  tenantApplicationsApiErrorResponse,
} from "@/lib/server/tenant-applications-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{
    id: string;
  }>;
};

export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const { id } = await context.params;

  try {
    const application =
      await withAdminAccessToken(
        (accessToken) =>
          getTenantApplication(accessToken, id),
      );

    return Response.json(
      application,
      {
        headers: {
          "Cache-Control":
            "private, no-store, max-age=0",
        },
      },
    );
  } catch (error) {
    return tenantApplicationsApiErrorResponse(error);
  }
}
