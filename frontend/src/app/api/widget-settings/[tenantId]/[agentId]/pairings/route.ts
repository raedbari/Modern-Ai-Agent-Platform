import {
  adminApiErrorResponse,
  createAdminWidgetConnectorPairing,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

import type {
  WidgetConnectorType,
} from "@/lib/server/admin-api";

type RouteContext = {
  params: Promise<{
    tenantId: string;
    agentId: string;
  }>;
};

const connectorTypes =
  new Set<WidgetConnectorType>([
    "wordpress",
    "react_next",
    "managed",
    "custom",
  ]);

function isObject(
  value: unknown,
): value is Record<string, unknown> {
  return (
    value !== null
    && typeof value === "object"
    && !Array.isArray(value)
  );
}

export async function POST(
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

  if (!isObject(body)) {
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

  const origin = body.origin;
  const connectorType = body.connector_type;

  if (
    Object.keys(body).length !== 2
    || typeof origin !== "string"
    || origin.trim().length === 0
    || origin.length > 255
    || typeof connectorType !== "string"
    || !connectorTypes.has(
      connectorType as WidgetConnectorType,
    )
  ) {
    return Response.json(
      {
        detail:
          "A valid origin and connector_type are required.",
      },
      {
        status: 422,
      },
    );
  }

  const normalizedOrigin = origin.trim();
  const normalizedConnectorType =
    connectorType as WidgetConnectorType;

  try {
    const pairing =
      await withAdminAccessToken(
        (accessToken) =>
          createAdminWidgetConnectorPairing(
            accessToken,
            tenantId,
            agentId,
            {
              origin: normalizedOrigin,
              connector_type:
                normalizedConnectorType,
            },
          ),
      );

    return Response.json(
      pairing,
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
