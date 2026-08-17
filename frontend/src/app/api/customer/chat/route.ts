import { testCustomerChat } from "@/lib/server/customer-resources-api";
import { tenantApiErrorResponse } from "@/lib/server/tenant-auth-api";
import { withTenantAccessToken } from "@/lib/server/tenant-session";

export async function POST(request: Request): Promise<Response> {
  const body = await request.json().catch(() => null) as { agentId?: unknown; message?: unknown; conversation_id?: unknown } | null;
  const agentId = typeof body?.agentId === "string" ? body.agentId.trim() : "";
  const message = typeof body?.message === "string" ? body.message.trim() : "";
  if (!agentId || !message) return Response.json({ detail: "Chatbot and message are required." }, { status: 400 });
  try {
    const result = await withTenantAccessToken((token) => testCustomerChat(token, agentId, {
      message,
      ...(typeof body?.conversation_id === "string" && body.conversation_id ? { conversation_id: body.conversation_id } : {}),
    }));
    return Response.json(result, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) { return tenantApiErrorResponse(error); }
}
