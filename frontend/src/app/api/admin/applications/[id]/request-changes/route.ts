import {
  requestApplicationChanges,
  tenantApplicationsApiErrorResponse,
} from "@/lib/server/tenant-applications-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{
    id: string;
  }>;
};

export async function POST(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const { id } = await context.params;

  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return Response.json(
      {
        detail: "Request body must be valid JSON.",
      },
      { status: 400 },
    );
  }

  if (
    body === null ||
    typeof body !== "object" ||
    typeof (body as { notes?: unknown }).notes !== "string" ||
    !(body as { notes: string }).notes.trim()
  ) {
    return Response.json(
      {
        detail: "notes is required and must be a non-empty string.",
      },
      { status: 400 },
    );
  }

  const notes = (body as { notes: string }).notes;

  try {
    const application =
      await withAdminAccessToken(
        (accessToken) =>
          requestApplicationChanges(accessToken, id, notes),
      );

    return Response.json(
      application,
      {
        headers: {
          "Cache-Control":
            "private, no-store, max-age=0",
        },
      },
    );
  } catch (error) {
    return tenantApplicationsApiErrorResponse(error);
  }
}
