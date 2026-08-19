import {
  adminApiErrorResponse,
  getAdminEvaluationDataset,
} from "@/lib/server/admin-api";
import { withAdminAccessToken } from "@/lib/server/admin-session";

type RouteContext = {
  params: Promise<{ name: string; version: string }>;
};

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const { name, version } = await context.params;
  try {
    const dataset = await withAdminAccessToken(
      (token) => getAdminEvaluationDataset(token, name, version),
    );
    return Response.json(dataset, {
      headers: { "Cache-Control": "private, no-store, max-age=0" },
    });
  } catch (error) {
    return adminApiErrorResponse(error);
  }
}
