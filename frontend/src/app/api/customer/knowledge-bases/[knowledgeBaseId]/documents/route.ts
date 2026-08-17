import { listCustomerDocuments, queueCustomerDocument } from "@/lib/server/customer-resources-api";
import { tenantApiErrorResponse } from "@/lib/server/tenant-auth-api";
import { withTenantAccessToken } from "@/lib/server/tenant-session";

type Context = { params: Promise<{ knowledgeBaseId: string }> };

function agentId(request: Request): string { return new URL(request.url).searchParams.get("agentId")?.trim() ?? ""; }

export async function GET(request: Request, context: Context): Promise<Response> {
  const { knowledgeBaseId } = await context.params;
  const agent = agentId(request);
  if (!agent) return Response.json({ detail: "Chatbot is required." }, { status: 400 });
  try {
    const items = await withTenantAccessToken((token) => listCustomerDocuments(token, agent, knowledgeBaseId));
    return Response.json(items, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) { return tenantApiErrorResponse(error); }
}

export async function POST(request: Request, context: Context): Promise<Response> {
  const { knowledgeBaseId } = await context.params;
  const agent = agentId(request);
  if (!agent) return Response.json({ detail: "Chatbot is required." }, { status: 400 });
  try {
    const form = await request.formData();
    const job = await withTenantAccessToken((token) => queueCustomerDocument(token, agent, knowledgeBaseId, form));
    return Response.json(job, { status: 202, headers: { "Cache-Control": "private, no-store" } });
  } catch (error) { return tenantApiErrorResponse(error); }
}
