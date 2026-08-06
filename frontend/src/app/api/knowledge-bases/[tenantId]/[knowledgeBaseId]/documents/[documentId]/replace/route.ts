import {
  adminApiErrorResponse,
  queueAdminKnowledgeDocumentReplacement,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{
    tenantId: string;
    knowledgeBaseId: string;
    documentId: string;
  }>;
};

export const dynamic = "force-dynamic";

export async function POST(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
    knowledgeBaseId,
    documentId,
  } = await context.params;

  try {
    const formData = await request.formData();

    const item =
      await withAdminAccessToken(
        (accessToken) =>
          queueAdminKnowledgeDocumentReplacement(
            accessToken,
            tenantId,
            knowledgeBaseId,
            documentId,
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
