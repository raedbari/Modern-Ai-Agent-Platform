import {
  AdminApiError,
  adminApiErrorResponse,
  createAdminAgent,
  listAdminTenants,
  listTenantAgents,
  type AgentAdmin,
  type TenantAdmin,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

import type {
  AgentDirectoryItem,
  AgentDirectoryResponse,
} from "@/lib/agents/contracts";

export const dynamic = "force-dynamic";

type TenantAgents = {
  tenant: TenantAdmin;
  agents: AgentAdmin[];
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

async function buildAgentDirectory(
  accessToken: string,
): Promise<AgentDirectoryResponse> {
  const warnings: string[] = [];

  const tenants = await listAdminTenants(
    accessToken,
  );

  const tenantAgents =
    await mapWithConcurrency(
      tenants,
      6,
      async (
        tenant,
      ): Promise<TenantAgents> => {
        try {
          return {
            tenant,
            agents:
              await listTenantAgents(
                accessToken,
                tenant.id,
              ),
          };
        } catch (error) {
          rethrowUnauthorized(error);

          warnings.push(
            `agents:${tenant.id}`,
          );

          return {
            tenant,
            agents: [],
          };
        }
      },
    );

  const items: AgentDirectoryItem[] =
    tenantAgents
      .flatMap(({ tenant, agents }) =>
        agents.map((agent) => ({
          id: agent.id,
          tenant_id: agent.tenant_id,
          tenant_name: tenant.name,
          name: agent.name,
          is_active: agent.is_active,
          knowledge_mode:
            agent.knowledge_mode,
          created_at: agent.created_at,
          updated_at: agent.updated_at,
        })),
      )
      .sort((left, right) => {
        const tenantComparison =
          left.tenant_name.localeCompare(
            right.tenant_name,
          );

        if (tenantComparison !== 0) {
          return tenantComparison;
        }

        return left.name.localeCompare(
          right.name,
        );
      });

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
      required: items.filter(
        (item) =>
          item.knowledge_mode ===
          "required",
      ).length,
      preferred: items.filter(
        (item) =>
          item.knowledge_mode ===
          "preferred",
      ).length,
      disabled: items.filter(
        (item) =>
          item.knowledge_mode ===
          "disabled",
      ).length,
    },
    items,
    warnings,
  };
}

export async function GET(): Promise<Response> {
  try {
    const directory =
      await withAdminAccessToken(
        buildAgentDirectory,
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
      tenant_id?: unknown;
      name?: unknown;
      system_prompt?: unknown;
      knowledge_mode?: unknown;
      contact_message?: unknown;
    } | null;

  const tenantId =
    typeof payload?.tenant_id === "string"
      ? payload.tenant_id.trim()
      : "";
  const name =
    typeof payload?.name === "string"
      ? payload.name.trim()
      : "";
  const mode = payload?.knowledge_mode;

  if (!tenantId || !name) {
    return Response.json(
      { detail: "tenant_id and name are required." },
      { status: 422 },
    );
  }

  if (
    mode !== undefined &&
    mode !== "required" &&
    mode !== "preferred" &&
    mode !== "disabled"
  ) {
    return Response.json(
      { detail: "Invalid knowledge_mode." },
      { status: 422 },
    );
  }

  try {
    const agent =
      await withAdminAccessToken(
        (accessToken) =>
          createAdminAgent(
            accessToken,
            tenantId,
            {
              name,
              system_prompt:
                typeof payload?.system_prompt === "string"
                  ? payload.system_prompt
                  : null,
              knowledge_mode:
                mode === "required" ||
                mode === "disabled"
                  ? mode
                  : "preferred",
              contact_message:
                typeof payload?.contact_message === "string"
                  ? payload.contact_message
                  : null,
            },
          ),
      );

    return Response.json(
      agent,
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
