import {
  adminApiErrorResponse,
  createAdminEvaluationRun,
  listAdminEvaluationRuns,
  type EvaluationRunCreatePayload,
} from "@/lib/server/admin-api";
import { withAdminAccessToken } from "@/lib/server/admin-session";

export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  try {
    const runs = await withAdminAccessToken(listAdminEvaluationRuns);
    return Response.json(runs, {
      headers: { "Cache-Control": "private, no-store, max-age=0" },
    });
  } catch (error) {
    return adminApiErrorResponse(error);
  }
}

export async function POST(request: Request): Promise<Response> {
  const payload = await request.json().catch(() => null) as
    EvaluationRunCreatePayload | null;
  if (payload === null) {
    return Response.json(
      { detail: "Invalid Evaluation request." },
      { status: 400 },
    );
  }
  try {
    const run = await withAdminAccessToken(
      (token) => createAdminEvaluationRun(token, payload),
    );
    return Response.json(run, {
      status: 202,
      headers: { "Cache-Control": "private, no-store, max-age=0" },
    });
  } catch (error) {
    return adminApiErrorResponse(error);
  }
}
