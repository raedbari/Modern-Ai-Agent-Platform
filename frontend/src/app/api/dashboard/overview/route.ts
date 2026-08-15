import {
  AdminApiError,
  adminApiErrorResponse,
  listAdminAuditEvents,
  listAdminTenants,
  listTenantAgents,
  listTenantApiKeys,
  type AdminAuditEvent,
  type AgentAdmin,
  type ApiKeyAdmin,
  type TenantAdmin,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

import type {
  DashboardOverview,
  DashboardTenantRank,
} from "@/lib/dashboard/overview";

export const dynamic = "force-dynamic";

type TenantAggregate = {
  tenant: TenantAdmin;
  agents: AgentAdmin[];
  apiKeys: ApiKeyAdmin[];
};

async function mapWithConcurrency<T, R>(
  items: readonly T[],
  concurrency: number,
  mapper: (
    item: T,
    index: number,
  ) => Promise<R>,
): Promise<R[]> {
  if (items.length === 0) {
    return [];
  }

  const results = new Array<R>(items.length);
  let cursor = 0;

  async function worker(): Promise<void> {
    while (true) {
      const index = cursor;
      cursor += 1;

      if (index >= items.length) {
        return;
      }

      results[index] = await mapper(
        items[index],
        index,
      );
    }
  }

  const workerCount = Math.min(
    Math.max(concurrency, 1),
    items.length,
  );

  await Promise.all(
    Array.from(
      { length: workerCount },
      () => worker(),
    ),
  );

  return results;
}

function rethrowUnauthorized(
  error: unknown,
): void {
  if (
    error instanceof AdminApiError &&
    error.status === 401
  ) {
    throw error;
  }
}

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

function mapAuditEvent(
  event: AdminAuditEvent,
) {
  return {
    id: event.id,
    event_type: event.event_type,
    outcome: event.outcome,
    target_type: event.target_type,
    target_id: event.target_id,
    created_at: event.created_at,
  };
}

async function buildOverview(
  accessToken: string,
): Promise<DashboardOverview> {
  const warnings: string[] = [];

  const tenants = await listAdminTenants(
    accessToken,
  );

  let auditEvents: AdminAuditEvent[] = [];

  try {
    auditEvents = await listAdminAuditEvents(
      accessToken,
      12,
    );
  } catch (error) {
    rethrowUnauthorized(error);
    warnings.push("audit");
  }

  const aggregates = await mapWithConcurrency(
    tenants,
    5,
    async (
      tenant,
    ): Promise<TenantAggregate> => {
      const [
        agentsResult,
        apiKeysResult,
      ] = await Promise.allSettled([
        listTenantAgents(
          accessToken,
          tenant.id,
        ),
        listTenantApiKeys(
          accessToken,
          tenant.id,
        ),
      ]);

      let agents: AgentAdmin[] = [];
      let apiKeys: ApiKeyAdmin[] = [];

      if (agentsResult.status === "fulfilled") {
        agents = agentsResult.value;
      } else {
        rethrowUnauthorized(
          agentsResult.reason,
        );

        warnings.push(
          `agents:${tenant.id}`,
        );
      }

      if (apiKeysResult.status === "fulfilled") {
        apiKeys = apiKeysResult.value;
      } else {
        rethrowUnauthorized(
          apiKeysResult.reason,
        );

        warnings.push(
          `api_keys:${tenant.id}`,
        );
      }

      return {
        tenant,
        agents,
        apiKeys,
      };
    },
  );

  const allAgents = aggregates.flatMap(
    (aggregate) => aggregate.agents,
  );

  const allApiKeys = aggregates.flatMap(
    (aggregate) => aggregate.apiKeys,
  );

  const now = Date.now();

  const activeApiKeys = allApiKeys.filter(
    (apiKey) => isActiveApiKey(
      apiKey,
      now,
    ),
  );

  const revokedApiKeys = allApiKeys.filter(
    (apiKey) =>
      apiKey.revoked_at !== null,
  );

  const expiredApiKeys = allApiKeys.filter(
    (apiKey) =>
      apiKey.expires_at !== null &&
      Date.parse(apiKey.expires_at) <= now,
  );

  const topTenants: DashboardTenantRank[] =
    aggregates
      .map((aggregate) => ({
        id: aggregate.tenant.id,
        name: aggregate.tenant.name,
        is_active:
          aggregate.tenant.is_active,
        agents_total:
          aggregate.agents.length,
        agents_active:
          aggregate.agents.filter(
            (agent) => agent.is_active,
          ).length,
        api_keys_active:
          aggregate.apiKeys.filter(
            (apiKey) => isActiveApiKey(
              apiKey,
              now,
            ),
          ).length,
      }))
      .sort((left, right) => {
        if (
          right.agents_total !==
          left.agents_total
        ) {
          return (
            right.agents_total -
            left.agents_total
          );
        }

        return left.name.localeCompare(
          right.name,
        );
      })
      .slice(0, 6);

  const recentAuditEvents = auditEvents
    .slice()
    .sort(
      (left, right) =>
        Date.parse(right.created_at) -
        Date.parse(left.created_at),
    )
    .slice(0, 10)
    .map(mapAuditEvent);

  return {
    generated_at: new Date().toISOString(),
    status:
      warnings.length === 0
        ? "healthy"
        : "partial",
    tenants: {
      total: tenants.length,
      active: tenants.filter(
        (tenant) => tenant.is_active,
      ).length,
      inactive: tenants.filter(
        (tenant) => !tenant.is_active,
      ).length,
    },
    agents: {
      total: allAgents.length,
      active: allAgents.filter(
        (agent) => agent.is_active,
      ).length,
      inactive: allAgents.filter(
        (agent) => !agent.is_active,
      ).length,
    },
    api_keys: {
      total: allApiKeys.length,
      active: activeApiKeys.length,
      inactive:
        allApiKeys.length -
        activeApiKeys.length,
      expired: expiredApiKeys.length,
      revoked: revokedApiKeys.length,
    },
    audit: {
      loaded: recentAuditEvents.length,
      success: recentAuditEvents.filter(
        (event) =>
          event.outcome === "success",
      ).length,
      failure: recentAuditEvents.filter(
        (event) =>
          event.outcome === "failure",
      ).length,
      recent: recentAuditEvents,
    },
    top_tenants: topTenants,
    warnings,
  };
}

export async function GET(): Promise<Response> {
  try {
    const overview =
      await withAdminAccessToken(
        buildOverview,
      );

    return Response.json(
      overview,
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
