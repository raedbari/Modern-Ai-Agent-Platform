import { type NextRequest } from "next/server";

import {
  withTenantAccessToken,
} from "@/lib/server/tenant-session";

import {
  listTenantConversations,
  tenantConversationsApiErrorResponse,
} from "@/lib/server/tenant-conversations-api";

export const dynamic =
  "force-dynamic";

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
): Promise<Response> {
  const params =
    request.nextUrl.searchParams;

  const agentId =
    params.get("agent_id")?.trim()
    || undefined;

  const limit = integer(
    params.get("limit"),
    100,
    1,
    200,
  );

  const offset = integer(
    params.get("offset"),
    0,
    0,
    Number.MAX_SAFE_INTEGER,
  );

  try {
    const data =
      await withTenantAccessToken(
        (accessToken) =>
          listTenantConversations(
            accessToken,
            {
              agentId,
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
