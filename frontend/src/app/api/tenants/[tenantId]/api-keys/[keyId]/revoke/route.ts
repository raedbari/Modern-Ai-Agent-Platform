import {
  adminApiErrorResponse,
  revokeAdminApiKey,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{
    tenantId: string;
    keyId: string;
  }>;
};

export async function POST(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
    keyId,
  } = await context.params;

  try {
    const apiKey =
      await withAdminAccessToken(
        (accessToken) =>
          revokeAdminApiKey(
            accessToken,
            tenantId,
            keyId,
          ),
      );

    return Response.json(
      apiKey,
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
