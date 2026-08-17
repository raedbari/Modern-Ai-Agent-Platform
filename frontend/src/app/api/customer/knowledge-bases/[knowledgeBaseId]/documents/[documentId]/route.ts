import { mutateCustomerDocument, replaceCustomerDocument } from "@/lib/server/customer-resources-api";
import { tenantApiErrorResponse } from "@/lib/server/tenant-auth-api";
import { withTenantAccessToken } from "@/lib/server/tenant-session";

type Context = { params: Promise<{ knowledgeBaseId: string; documentId: string }> };
function values(request: Request) { const url = new URL(request.url); return { agentId: url.searchParams.get("agentId")?.trim() ?? "", action: url.searchParams.get("action") ?? "" }; }

export async function DELETE(request: Request, context: Context): Promise<Response> {
  const { knowledgeBaseId, documentId } = await context.params; const { agentId } = values(request);
  if (!agentId) return Response.json({ detail: "Chatbot is required." }, { status: 400 });
  try { await withTenantAccessToken((token) => mutateCustomerDocument(token, agentId, knowledgeBaseId, documentId, "delete")); return new Response(null, { status: 204 }); }
  catch (error) { return tenantApiErrorResponse(error); }
}

export async function POST(request: Request, context: Context): Promise<Response> {
  const { knowledgeBaseId, documentId } = await context.params; const { agentId, action } = values(request);
  if (!agentId) return Response.json({ detail: "Chatbot is required." }, { status: 400 });
  try {
    const result = action === "replace"
      ? await withTenantAccessToken(async (token) => replaceCustomerDocument(token, agentId, knowledgeBaseId, documentId, await request.formData()))
      : await withTenantAccessToken((token) => mutateCustomerDocument(token, agentId, knowledgeBaseId, documentId, "archive"));
    return Response.json(result, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) { return tenantApiErrorResponse(error); }
}
