import {
  adminApiErrorResponse,
  getAdminEvaluationRun,
} from "@/lib/server/admin-api";
import { withAdminAccessToken } from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{ runId: string }>;
};

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const { runId } = await context.params;
  try {
    const run = await withAdminAccessToken(
      (token) => getAdminEvaluationRun(token, runId),
    );
    return Response.json(run, {
      headers: { "Cache-Control": "private, no-store, max-age=0" },
    });
  } catch (error) {
    return adminApiErrorResponse(error);
  }
}
