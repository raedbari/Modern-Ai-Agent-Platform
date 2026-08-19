import { getCustomerWidgetInstallation } from "@/lib/server/customer-resources-api";
import { tenantApiErrorResponse } from "@/lib/server/tenant-auth-api";
import { withTenantAccessToken } from "@/lib/server/tenant-session";

type Context = { params: Promise<{ agentId: string }> };

export async function GET(request: Request, context: Context): Promise<Response> {
  const { agentId } = await context.params;
  const url = new URL(request.url);
  const pairingId = url.searchParams.get("pairing_id") ?? undefined;
  const origin = url.searchParams.get("origin") ?? undefined;

  try {
    const result = await withTenantAccessToken((token) =>
      getCustomerWidgetInstallation(token, agentId, { pairingId, origin }),
    );
    return Response.json(result, {
      headers: { "Cache-Control": "private, no-store" },
    });
  } catch (error) {
    return tenantApiErrorResponse(error);
  }
}
