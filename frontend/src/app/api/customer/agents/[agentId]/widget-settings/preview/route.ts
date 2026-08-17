import { bootstrapCustomerWidgetPreview } from "@/lib/server/customer-resources-api";
import { tenantApiErrorResponse } from "@/lib/server/tenant-auth-api";
import { withTenantAccessToken } from "@/lib/server/tenant-session";

type Context = { params: Promise<{ agentId: string }> };
export async function POST(request: Request, context: Context): Promise<Response> {
  const { agentId } = await context.params;
  const origin = request.headers.get("origin");
  if (!origin) return Response.json({ detail: "A valid Origin is required." }, { status: 403 });
  try { return Response.json(await withTenantAccessToken((token) => bootstrapCustomerWidgetPreview(token, agentId, origin)), { headers: { "Cache-Control": "private, no-store" } }); }
  catch (error) { return tenantApiErrorResponse(error); }
}
