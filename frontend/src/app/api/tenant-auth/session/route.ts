import {
  tenantApiErrorResponse,
} from "@/lib/server/tenant-auth-api";

import {
  getCurrentTenantProfile,
} from "@/lib/server/tenant-session";

export async function GET(): Promise<Response> {
  try {
    const profile =
      await getCurrentTenantProfile();

    return Response.json(
      profile,
      {
        headers: {
          "Cache-Control": "no-store",
        },
      },
    );
  } catch (error) {
    return tenantApiErrorResponse(error);
  }
}
