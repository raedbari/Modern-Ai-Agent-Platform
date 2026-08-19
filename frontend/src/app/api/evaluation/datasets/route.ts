import {
  adminApiErrorResponse,
  listAdminEvaluationDatasets,
  uploadAdminEvaluationDataset,
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

export async function POST(request: Request): Promise<Response> {
  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return Response.json(
      { detail: "Invalid dataset upload form." },
      { status: 400 },
    );
  }
  try {
    const dataset = await withAdminAccessToken(
      (token) => uploadAdminEvaluationDataset(token, formData),
    );
    return Response.json(dataset, {
      status: 201,
      headers: { "Cache-Control": "private, no-store, max-age=0" },
    });
  } catch (error) {
    return adminApiErrorResponse(error);
  }
}
