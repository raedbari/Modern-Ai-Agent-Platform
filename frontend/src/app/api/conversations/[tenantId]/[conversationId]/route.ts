
import {
  adminApiErrorResponse,
  getAdminConversation,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{
    tenantId: string;
    conversationId: string;
  }>;
};

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
    conversationId,
  } = await context.params;

  try {
    const conversation =
      await withAdminAccessToken(
        (accessToken) =>
          getAdminConversation(
            accessToken,
            tenantId,
            conversationId,
          ),
      );

    return Response.json(
      conversation,
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
