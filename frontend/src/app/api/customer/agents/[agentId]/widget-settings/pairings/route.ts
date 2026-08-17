import { createCustomerWidgetPairing } from "@/lib/server/customer-resources-api";
import { tenantApiErrorResponse } from "@/lib/server/tenant-auth-api";
import { withTenantAccessToken } from "@/lib/server/tenant-session";

type Context = { params: Promise<{ agentId: string }> };
export async function POST(request: Request, context: Context): Promise<Response> {
  const { agentId } = await context.params;
  const body = await request.json().catch(() => null) as { origin?: unknown; connector_type?: unknown } | null;
  if (typeof body?.origin !== "string" || !["wordpress", "react_next", "managed", "custom"].includes(String(body.connector_type))) return Response.json({ detail: "Valid origin and connector type are required." }, { status: 422 });
  try {
    const result = await withTenantAccessToken((token) => createCustomerWidgetPairing(token, agentId, { origin: body.origin as string, connector_type: body.connector_type as "wordpress" | "react_next" | "managed" | "custom" }));
    return Response.json(result, { status: 201, headers: { "Cache-Control": "private, no-store" } });
  } catch (error) { return tenantApiErrorResponse(error); }
}
