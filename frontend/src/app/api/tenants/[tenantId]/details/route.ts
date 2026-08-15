import {
  adminApiErrorResponse,
  getAdminTenant,
  listTenantAgents,
  listTenantApiKeys,
  type ApiKeyAdmin,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

import type {
  TenantDetailsResponse,
} from "@/lib/tenants/contracts";

export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{
    tenantId: string;
  }>;
};

function isActiveApiKey(
  apiKey: ApiKeyAdmin,
  now: number,
): boolean {
  if (
    !apiKey.is_active ||
    apiKey.revoked_at !== null
  ) {
    return false;
  }

  if (
    apiKey.expires_at !== null &&
    Date.parse(apiKey.expires_at) <= now
  ) {
    return false;
  }

  return true;
}

export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
  } = await context.params;

  try {
    const details =
      await withAdminAccessToken(
        async (
          accessToken,
        ): Promise<TenantDetailsResponse> => {
          const [
            tenant,
            agents,
            apiKeys,
          ] = await Promise.all([
            getAdminTenant(
              accessToken,
              tenantId,
            ),
            listTenantAgents(
              accessToken,
              tenantId,
            ),
            listTenantApiKeys(
              accessToken,
              tenantId,
            ),
          ]);

          const now = Date.now();

          const sortedAgents = agents
            .slice()
            .sort((left, right) =>
              left.name.localeCompare(
                right.name,
              ),
            );

          const sortedApiKeys = apiKeys
            .slice()
            .sort(
              (left, right) =>
                Date.parse(right.created_at) -
                Date.parse(left.created_at),
            );

          return {
            generated_at:
              new Date().toISOString(),
            tenant,
            summary: {
              agents_total:
                sortedAgents.length,
              agents_active:
                sortedAgents.filter(
                  (agent) =>
                    agent.is_active,
                ).length,
              api_keys_total:
                sortedApiKeys.length,
              api_keys_active:
                sortedApiKeys.filter(
                  (apiKey) =>
                    isActiveApiKey(
                      apiKey,
                      now,
                    ),
                ).length,
              api_keys_revoked:
                sortedApiKeys.filter(
                  (apiKey) =>
                    apiKey.revoked_at !== null,
                ).length,
              api_keys_expired:
                sortedApiKeys.filter(
                  (apiKey) =>
                    apiKey.expires_at !== null &&
                    Date.parse(
                      apiKey.expires_at,
                    ) <= now,
                ).length,
            },
            agents: sortedAgents,
            api_keys: sortedApiKeys,
          };
        },
      );

    return Response.json(
      details,
      {
        headers: {
          "Cache-Control":
            "private, no-store, max-age=0",
        },
      },
    );
  } catch (error) {
    return adminApiErrorResponse(error);
  }
}
