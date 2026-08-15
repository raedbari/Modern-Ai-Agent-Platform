import {
  adminApiErrorResponse,
  listAdminKnowledgeDocuments,
  queueAdminKnowledgeDocument,
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
    const items =
      await withAdminAccessToken(
        (accessToken) =>
          listAdminKnowledgeDocuments(
            accessToken,
            tenantId,
            knowledgeBaseId,
          ),
      );

    return Response.json(
      items,
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

export async function POST(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
    knowledgeBaseId,
  } = await context.params;

  try {
    const formData = await request.formData();

    const item =
      await withAdminAccessToken(
        (accessToken) =>
          queueAdminKnowledgeDocument(
            accessToken,
            tenantId,
            knowledgeBaseId,
            formData,
          ),
      );

    return Response.json(
      item,
      {
        status: 202,
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
