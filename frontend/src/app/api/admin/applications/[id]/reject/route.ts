import {
  rejectTenantApplication,
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

export async function POST(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const { id } = await context.params;

  let body: unknown;

  try {
    body = await request.json();
  } catch {
    body = {};
  }

  const reason =
    body !== null &&
    typeof body === "object" &&
    typeof (body as { reason?: unknown }).reason === "string"
      ? (body as { reason: string }).reason
      : undefined;

  try {
    const application =
      await withAdminAccessToken(
        (accessToken) =>
          rejectTenantApplication(accessToken, id, reason),
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
