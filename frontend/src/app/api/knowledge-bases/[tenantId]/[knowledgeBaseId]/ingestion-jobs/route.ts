import {
  adminApiErrorResponse,
  listAdminKnowledgeIngestionJobs,
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
    knowledgeBaseId,
  } = await context.params;

  const rawLimit =
    new URL(request.url)
      .searchParams
      .get("limit");

  let limit = 100;

  if (rawLimit !== null) {
    const parsedLimit = Number(rawLimit);

    if (
      !Number.isInteger(parsedLimit) ||
      parsedLimit < 1 ||
      parsedLimit > 200
    ) {
      return validationError(
        "limit must be an integer between 1 and 200.",
      );
    }

    limit = parsedLimit;
  }

  try {
    const items =
      await withAdminAccessToken(
        (accessToken) =>
          listAdminKnowledgeIngestionJobs(
            accessToken,
            tenantId,
            knowledgeBaseId,
            limit,
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
