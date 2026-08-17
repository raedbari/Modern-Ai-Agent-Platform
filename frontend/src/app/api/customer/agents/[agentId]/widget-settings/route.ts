import { getCustomerWidgetSettings, putCustomerWidgetSettings } from "@/lib/server/customer-resources-api";
import { tenantApiErrorResponse } from "@/lib/server/tenant-auth-api";
import { withTenantAccessToken } from "@/lib/server/tenant-session";

type Context = { params: Promise<{ agentId: string }> };
function browserSafe(settings: Awaited<ReturnType<typeof getCustomerWidgetSettings>>) {
  const safe: Partial<typeof settings> = { ...settings };
  delete safe.tenant_id;
  delete safe.agent_id;
  return safe;
}
export async function GET(_request: Request, context: Context): Promise<Response> {
  const { agentId } = await context.params;
  try { return Response.json(browserSafe(await withTenantAccessToken((token) => getCustomerWidgetSettings(token, agentId))), { headers: { "Cache-Control": "private, no-store" } }); }
  catch (error) { return tenantApiErrorResponse(error); }
}
export async function PUT(request: Request, context: Context): Promise<Response> {
  const { agentId } = await context.params; const body = await request.json().catch(() => null);
  if (!body || typeof body !== "object") return Response.json({ detail: "Invalid JSON payload." }, { status: 400 });
  try { return Response.json(browserSafe(await withTenantAccessToken((token) => putCustomerWidgetSettings(token, agentId, body))), { headers: { "Cache-Control": "private, no-store" } }); }
  catch (error) { return tenantApiErrorResponse(error); }
}
