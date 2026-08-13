import {
  AdminApiError,
  adminApiErrorResponse,
  createAdminTenant,
  listAdminTenants,
  listTenantAgents,
  listTenantApiKeys,
  type AgentAdmin,
  type ApiKeyAdmin,
  type TenantAdmin,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

import type {
  TenantDirectoryItem,
  TenantDirectoryResponse,
} from "@/lib/tenants/contracts";

export const dynamic = "force-dynamic";

type Aggregate = {
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

  await Promise.all(
    Array.from(
      {
        length: Math.min(
          Math.max(concurrency, 1),
          items.length,
        ),
      },
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

async function buildTenantDirectory(
  accessToken: string,
): Promise<TenantDirectoryResponse> {
  const warnings: string[] = [];
  const tenants = await listAdminTenants(
    accessToken,
  );

  const aggregates = await mapWithConcurrency(
    tenants,
    5,
    async (
      tenant,
    ): Promise<Aggregate> => {
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

  const now = Date.now();

  const items: TenantDirectoryItem[] =
    aggregates
      .map((aggregate) => ({
        id: aggregate.tenant.id,
        name: aggregate.tenant.name,
        is_active:
          aggregate.tenant.is_active,
        created_at:
          aggregate.tenant.created_at,
        updated_at:
          aggregate.tenant.updated_at,
        agents_total:
          aggregate.agents.length,
        agents_active:
          aggregate.agents.filter(
            (agent) => agent.is_active,
          ).length,
        api_keys_total:
          aggregate.apiKeys.length,
        api_keys_active:
          aggregate.apiKeys.filter(
            (apiKey) =>
              isActiveApiKey(
                apiKey,
                now,
              ),
          ).length,
      }))
      .sort((left, right) =>
        left.name.localeCompare(
          right.name,
        ),
      );

  return {
    generated_at: new Date().toISOString(),
    status:
      warnings.length === 0
        ? "healthy"
        : "partial",
    summary: {
      total: items.length,
      active: items.filter(
        (item) => item.is_active,
      ).length,
      inactive: items.filter(
        (item) => !item.is_active,
      ).length,
      agents_total: items.reduce(
        (total, item) =>
          total + item.agents_total,
        0,
      ),
      agents_active: items.reduce(
        (total, item) =>
          total + item.agents_active,
        0,
      ),
      api_keys_total: items.reduce(
        (total, item) =>
          total + item.api_keys_total,
        0,
      ),
      api_keys_active: items.reduce(
        (total, item) =>
          total + item.api_keys_active,
        0,
      ),
    },
    items,
    warnings,
  };
}

export async function GET(): Promise<Response> {
  try {
    const directory =
      await withAdminAccessToken(
        buildTenantDirectory,
      );

    return Response.json(
      directory,
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

export async function POST(
  request: Request,
): Promise<Response> {
  const payload = await request
    .json()
    .catch(() => null) as {
      name?: unknown;
      is_active?: unknown;
    } | null;

  const name =
    typeof payload?.name === "string"
      ? payload.name.trim()
      : "";

  if (!name) {
    return Response.json(
      { detail: "Tenant name is required." },
      { status: 422 },
    );
  }

  try {
    const tenant =
      await withAdminAccessToken(
        (accessToken) =>
          createAdminTenant(
            accessToken,
            {
              name,
              is_active:
                typeof payload?.is_active === "boolean"
                  ? payload.is_active
                  : true,
            },
          ),
      );

    return Response.json(
      tenant,
      {
        status: 201,
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
