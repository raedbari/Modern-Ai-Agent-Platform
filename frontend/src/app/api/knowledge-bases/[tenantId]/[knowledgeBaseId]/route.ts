import {
  adminApiErrorResponse,
  getAdminKnowledgeBase,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{
    tenantId: string;
    knowledgeBaseId: string;
  }>;
};

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
    knowledgeBaseId,
  } = await context.params;

  try {
    const item =
      await withAdminAccessToken(
        (accessToken) =>
          getAdminKnowledgeBase(
            accessToken,
            tenantId,
            knowledgeBaseId,
          ),
      );

    return Response.json(
      item,
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
