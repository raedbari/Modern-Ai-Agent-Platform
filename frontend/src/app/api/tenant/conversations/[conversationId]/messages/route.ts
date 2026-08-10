import { type NextRequest } from "next/server";

import {
  withTenantAccessToken,
} from "@/lib/server/tenant-session";

import {
  listTenantConversationMessages,
  tenantConversationsApiErrorResponse,
} from "@/lib/server/tenant-conversations-api";

export const dynamic =
  "force-dynamic";

type RouteContext = {
  params: Promise<{
    conversationId: string;
  }>;
};

function integer(
  raw: string | null,
  fallback: number,
  min: number,
  max: number,
): number {
  if (!raw) return fallback;

  const value =
    Number.parseInt(raw, 10);

  if (!Number.isFinite(value)) {
    return fallback;
  }

  return Math.min(
    Math.max(value, min),
    max,
  );
}

export async function GET(
  request: NextRequest,
  context: RouteContext,
): Promise<Response> {
  const {
    conversationId,
  } = await context.params;

  const limit = integer(
    request.nextUrl.searchParams.get(
      "limit",
    ),
    200,
    1,
    500,
  );

  const offset = integer(
    request.nextUrl.searchParams.get(
      "offset",
    ),
    0,
    0,
    Number.MAX_SAFE_INTEGER,
  );

  try {
    const data =
      await withTenantAccessToken(
        (accessToken) =>
          listTenantConversationMessages(
            accessToken,
            conversationId,
            {
              limit,
              offset,
            },
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
