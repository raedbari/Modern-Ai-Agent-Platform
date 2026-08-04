import {
  adminApiErrorResponse,
  updateAdminAgentConfiguration,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

import type {
  AgentConfigUpdatePayload,
} from "@/lib/server/admin-api";

type RouteContext = {
  params: Promise<{
    tenantId: string;
    agentId: string;
  }>;
};

const knowledgeModes = new Set([
  "required",
  "preferred",
  "disabled",
]);

export async function PATCH(
  request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
    agentId,
  } = await context.params;

  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return Response.json(
      {
        detail:
          "Request body must be valid JSON.",
      },
      {
        status: 400,
      },
    );
  }

  if (
    body === null ||
    typeof body !== "object" ||
    Array.isArray(body)
  ) {
    return Response.json(
      {
        detail:
          "Request body must be an object.",
      },
      {
        status: 422,
      },
    );
  }

  const raw = body as {
    name?: unknown;
    knowledge_mode?: unknown;
  };

  const payload:
    AgentConfigUpdatePayload = {};

  if (raw.name !== undefined) {
    if (
      typeof raw.name !== "string" ||
      raw.name.trim().length === 0 ||
      raw.name.trim().length > 255
    ) {
      return Response.json(
        {
          detail:
            "name must contain 1 to 255 characters.",
        },
        {
          status: 422,
        },
      );
    }

    payload.name = raw.name.trim();
  }

  if (
    raw.knowledge_mode !== undefined
  ) {
    if (
      typeof raw.knowledge_mode !==
        "string" ||
      !knowledgeModes.has(
        raw.knowledge_mode,
      )
    ) {
      return Response.json(
        {
          detail:
            "knowledge_mode is invalid.",
        },
        {
          status: 422,
        },
      );
    }

    payload.knowledge_mode =
      raw.knowledge_mode as
        | "required"
        | "preferred"
        | "disabled";
  }

  if (
    payload.name === undefined &&
    payload.knowledge_mode === undefined
  ) {
    return Response.json(
      {
        detail:
          "At least one editable field is required.",
      },
      {
        status: 422,
      },
    );
  }

  try {
    const agent =
      await withAdminAccessToken(
        (accessToken) =>
          updateAdminAgentConfiguration(
            accessToken,
            tenantId,
            agentId,
            payload,
          ),
      );

    return Response.json(
      agent,
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
