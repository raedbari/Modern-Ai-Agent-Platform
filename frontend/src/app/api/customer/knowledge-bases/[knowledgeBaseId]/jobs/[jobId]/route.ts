import { getCustomerDocumentJob } from "@/lib/server/customer-resources-api";
import { tenantApiErrorResponse } from "@/lib/server/tenant-auth-api";
import { withTenantAccessToken } from "@/lib/server/tenant-session";

type Context = { params: Promise<{ knowledgeBaseId: string; jobId: string }> };
export async function GET(request: Request, context: Context): Promise<Response> {
  const { knowledgeBaseId, jobId } = await context.params;
  const agentId = new URL(request.url).searchParams.get("agentId")?.trim() ?? "";
  if (!agentId) return Response.json({ detail: "Chatbot is required." }, { status: 400 });
  try {
    const job = await withTenantAccessToken((token) => getCustomerDocumentJob(token, agentId, knowledgeBaseId, jobId));
    return Response.json(job, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) { return tenantApiErrorResponse(error); }
}
