import {
  listTenantApplications,
  tenantApplicationsApiErrorResponse,
} from "@/lib/server/tenant-applications-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  try {
    const applications =
      await withAdminAccessToken(
        (accessToken) =>
          listTenantApplications(accessToken),
      );

    return Response.json(
      applications,
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
