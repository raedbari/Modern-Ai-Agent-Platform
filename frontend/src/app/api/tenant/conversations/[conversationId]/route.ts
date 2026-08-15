import {
  withTenantAccessToken,
} from "@/lib/server/tenant-session";

import {
  getTenantConversation,
  tenantConversationsApiErrorResponse,
} from "@/lib/server/tenant-conversations-api";

export const dynamic =
  "force-dynamic";

type RouteContext = {
  params: Promise<{
    conversationId: string;
  }>;
};

export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    conversationId,
  } = await context.params;

  try {
    const data =
      await withTenantAccessToken(
        (accessToken) =>
          getTenantConversation(
            accessToken,
            conversationId,
          ),
      );

    return Response.json(
      data,
      {
        headers: {
          "Cache-Control":
            "private, no-store, max-age=0",
        },
      },
    );
  } catch (error) {
    return tenantConversationsApiErrorResponse(
      error,
    );
  }
}
