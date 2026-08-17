import { assignCustomerKnowledgeBase } from "@/lib/server/customer-resources-api";
import { tenantApiErrorResponse } from "@/lib/server/tenant-auth-api";
import { withTenantAccessToken } from "@/lib/server/tenant-session";

type Context = { params: Promise<{ agentId: string; knowledgeBaseId: string }> };

export async function PUT(_request: Request, context: Context): Promise<Response> {
  const { agentId, knowledgeBaseId } = await context.params;
  try {
    const item = await withTenantAccessToken((token) =>
      assignCustomerKnowledgeBase(token, agentId, knowledgeBaseId));
    return Response.json(item, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    return tenantApiErrorResponse(error);
  }
}
