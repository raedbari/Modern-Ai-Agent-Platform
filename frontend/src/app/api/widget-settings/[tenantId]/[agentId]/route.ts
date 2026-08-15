import {
  adminApiErrorResponse,
  getAdminWidgetSettings,
  putAdminWidgetSettings,
} from "@/lib/server/admin-api";

import {
  withAdminAccessToken,
} from "@/lib/server/admin-session";

import type {
  WidgetSettingsUpdatePayload,
} from "@/lib/server/admin-api";

type RouteContext = {
  params: Promise<{
    tenantId: string;
    agentId: string;
  }>;
};

const hexColorPattern =
  /^#[0-9A-Fa-f]{6}$/;

const topLevelKeys = new Set([
  "is_enabled",
  "display_name",
  "greeting",
  "theme",
  "allowed_origins",
]);

const themeKeys = new Set([
  "primaryColor",
  "textColor",
  "launcherColor",
  "headerColor",
  "userMessageColor",
  "position",
  "appearance",
]);

function isObject(
  value: unknown,
): value is Record<string, unknown> {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value)
  );
}

function hasExactKeys(
  value: Record<string, unknown>,
  expected: Set<string>,
): boolean {
  const keys = Object.keys(value);

  return (
    keys.length === expected.size &&
    keys.every((key) => expected.has(key))
  );
}

function isNullableBoundedString(
  value: unknown,
  maxLength: number,
): value is string | null {
  return (
    value === null ||
    (
      typeof value === "string" &&
      value.length <= maxLength
    )
  );
}

function validationError(
  detail: string,
): Response {
  return Response.json(
    {
      detail,
    },
    {
      status: 422,
      headers: {
        "Cache-Control":
          "private, no-store, max-age=0",
      },
    },
  );
}

export async function GET(
  _request: Request,
  context: RouteContext,
): Promise<Response> {
  const {
    tenantId,
    agentId,
  } = await context.params;

  try {
    const settings =
      await withAdminAccessToken(
        (accessToken) =>
          getAdminWidgetSettings(
            accessToken,
            tenantId,
            agentId,
          ),
      );

    return Response.json(
      settings,
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

export async function PUT(
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
        headers: {
          "Cache-Control":
            "private, no-store, max-age=0",
        },
      },
    );
  }

  if (!isObject(body)) {
    return validationError(
      "Request body must be an object.",
    );
  }

  if (!hasExactKeys(body, topLevelKeys)) {
    return validationError(
      "A complete Widget configuration is required.",
    );
  }

  if (
    typeof body.is_enabled !== "boolean"
  ) {
    return validationError(
      "is_enabled must be a boolean.",
    );
  }

  if (
    !isNullableBoundedString(
      body.display_name,
      255,
    )
  ) {
    return validationError(
      "display_name must be null or contain "
      + "at most 255 characters.",
    );
  }

  if (
    !isNullableBoundedString(
      body.greeting,
      500,
    )
  ) {
    return validationError(
      "greeting must be null or contain "
      + "at most 500 characters.",
    );
  }

  if (
    !Array.isArray(body.allowed_origins) ||
    body.allowed_origins.length > 50
  ) {
    return validationError(
      "allowed_origins must contain "
      + "at most 50 entries.",
    );
  }

  const origins: string[] = [];

  for (
    const rawOrigin
    of body.allowed_origins
  ) {
    if (typeof rawOrigin !== "string") {
      return validationError(
        "Every allowed origin must be a string.",
      );
    }

    const origin = rawOrigin.trim();

    if (
      origin.length === 0 ||
      origin.length > 255
    ) {
      return validationError(
        "Every allowed origin must contain "
        + "1 to 255 characters.",
      );
    }

    if (origins.includes(origin)) {
      return validationError(
        "Duplicate allowed origins are not permitted.",
      );
    }

    origins.push(origin);
  }

  if (!isObject(body.theme)) {
    return validationError(
      "theme must be an object.",
    );
  }

  if (
    !hasExactKeys(
      body.theme,
      themeKeys,
    )
  ) {
    return validationError(
      "A complete Widget theme is required.",
    );
  }

  const colorFields = [
    "primaryColor",
    "textColor",
    "launcherColor",
    "headerColor",
    "userMessageColor",
  ] as const;

  const colors: Record<
    typeof colorFields[number],
    string
  > = {
    primaryColor: "",
    textColor: "",
    launcherColor: "",
    headerColor: "",
    userMessageColor: "",
  };

  for (const field of colorFields) {
    const value = body.theme[field];

    if (
      typeof value !== "string" ||
      !hexColorPattern.test(value)
    ) {
      return validationError(
        `${field} must be a six-digit hexadecimal color.`,
      );
    }

    colors[field] = value.toUpperCase();
  }

  const position = body.theme.position;

  if (
    position !== "left" &&
    position !== "right"
  ) {
    return validationError(
      "theme.position must be left or right.",
    );
  }

  const appearance = body.theme.appearance;

  if (
    appearance !== "light" &&
    appearance !== "dark"
  ) {
    return validationError(
      "theme.appearance must be light or dark.",
    );
  }

  const payload:
    WidgetSettingsUpdatePayload = {
      is_enabled: body.is_enabled,
      display_name: body.display_name,
      greeting: body.greeting,
      allowed_origins: origins,
      theme: {
        ...colors,
        position,
        appearance,
      },
    };

  try {
    const settings =
      await withAdminAccessToken(
        (accessToken) =>
          putAdminWidgetSettings(
            accessToken,
            tenantId,
            agentId,
            payload,
          ),
      );

    return Response.json(
      settings,
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
