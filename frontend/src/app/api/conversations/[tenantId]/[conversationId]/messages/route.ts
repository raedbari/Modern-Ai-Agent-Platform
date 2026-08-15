
import {
  adminApiErrorResponse,
  listAdminConversationMessages,
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

function parseInteger(
  value: string | null,
  fallback: number,
  minimum: number,
  maximum: number,
): number {
  if (value === null) {
    return fallback;
  }

  const parsed = Number.parseInt(
    value,
    10,
  );

  if (!Number.isFinite(parsed)) {
    return fallback;
  }

  return Math.min(
    Math.max(parsed, minimum),
    maximum,
  );
}

export async function GET(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
    conversationId,
  } = await context.params;

  const searchParams =
    new URL(request.url).searchParams;

  const limit = parseInteger(
    searchParams.get("limit"),
    200,
    1,
    500,
  );

  const offset = parseInteger(
    searchParams.get("offset"),
    0,
    0,
    Number.MAX_SAFE_INTEGER,
  );

  try {
    const messages =
      await withAdminAccessToken(
        (accessToken) =>
          listAdminConversationMessages(
            accessToken,
            tenantId,
            conversationId,
            {
              limit,
              offset,
            },
          ),
      );

    return Response.json(
      messages,
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
