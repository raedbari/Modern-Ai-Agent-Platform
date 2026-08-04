import {
  adminApiErrorResponse,
  listAdminKnowledgeBases,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{
    tenantId: string;
  }>;
};

export const dynamic = "force-dynamic";

function validationError(
  detail: string,
): Response {
  return Response.json(
    {
      detail,
    },
    {
      status: 422,
      headers: {
        "Cache-Control":
          "private, no-store, max-age=0",
      },
    },
  );
}

export async function GET(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
  } = await context.params;

  const rawAgentId =
    new URL(request.url)
      .searchParams
      .get("agentId");

  const agentId =
    rawAgentId?.trim() || undefined;

  if (
    agentId !== undefined &&
    agentId.length > 128
  ) {
    return validationError(
      "agentId must contain at most 128 characters.",
    );
  }

  try {
    const items =
      await withAdminAccessToken(
        (accessToken) =>
          listAdminKnowledgeBases(
            accessToken,
            tenantId,
            agentId,
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
