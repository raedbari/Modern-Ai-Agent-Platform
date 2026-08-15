import {
  adminApiErrorResponse,
  revokeAllAdminApiKeys,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{
    tenantId: string;
  }>;
};

export async function POST(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
  } = await context.params;

  try {
    const result =
      await withAdminAccessToken(
        (accessToken) =>
          revokeAllAdminApiKeys(
            accessToken,
            tenantId,
          ),
      );

    return Response.json(
      result,
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
