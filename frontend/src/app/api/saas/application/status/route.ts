import {
  getApplicationStatus,
  saasApiErrorResponse,
} from "@/lib/server/saas-api";

import {
  readTenantSessionCookies,
} from "@/lib/server/tenant-session";

export async function GET(): Promise<Response> {
  const { accessToken } =
    await readTenantSessionCookies();

  if (!accessToken) {
    return Response.json(
      {
        detail: "Unauthorized.",
      },
      {
        status: 401,
        headers: {
          "Cache-Control": "no-store",
        },
      },
    );
  }

  try {
    const status =
      await getApplicationStatus(accessToken);

    return Response.json(
      status,
      {
        headers: {
          "Cache-Control": "no-store",
        },
      },
    );
  } catch (error) {
    return saasApiErrorResponse(error);
  }
}
