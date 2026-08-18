import {
  adminApiErrorResponse,
  listAdminEvaluationDatasets,
} from "@/lib/server/admin-api";
import { withAdminAccessToken } from "@/lib/server/admin-session";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  try {
    const datasets = await withAdminAccessToken(
      listAdminEvaluationDatasets,
    );
    return Response.json(datasets, {
      headers: { "Cache-Control": "private, no-store, max-age=0" },
    });
  } catch (error) {
    return adminApiErrorResponse(error);
  }
}
