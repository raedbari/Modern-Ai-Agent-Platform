"use client";

import {
  Bot,
  Check,
  Clipboard,
  Globe2,
  Loader2,
  MessageCircle,
  Paintbrush,
  Power,
  RefreshCw,
  Save,
  Search,
  ShieldCheck,
  Undo2,
} from "lucide-react";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  LiveWidgetPreview,
} from "@/components/widget-settings/live-widget-preview";

import {
  createDefaultWidgetPayload,
} from "@/lib/widget-settings/contracts";

import type {
  WidgetSettingsPutPayload,
  WidgetSettingsRecord,
  WidgetTheme,
} from "@/lib/widget-settings/contracts";

type AgentOption = {
  id: string;
  tenant_id: string;
  name: string;
  tenant_name: string;
  is_active: boolean;
};

type OriginValidation = {
  origins: string[];
  error: string | null;
};


type WidgetConnectorType =
  | "wordpress"
  | "react_next"
  | "managed"
  | "custom";

type WidgetConnectorPairing = {
  pairing_id: string;
  pairing_code: string;
  origin: string;
  connector_type: WidgetConnectorType;
  expires_at: string;
  expires_in: number;
};

const copy = {
  title:
    "\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0648\u064a\u062f\u062c\u062a",
  subtitle:
    "\u062e\u0635\u0635 \u0646\u0627\u0641\u0630\u0629 \u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0629 \u0644\u0643\u0644 \u0648\u0643\u064a\u0644 \u0645\u0639 \u0645\u0639\u0627\u064a\u0646\u0629 \u0645\u0628\u0627\u0634\u0631\u0629 \u0642\u0628\u0644 \u0627\u0644\u062d\u0641\u0638.",
  refreshAgents:
    "\u062a\u062d\u062f\u064a\u062b \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  loadingAgents:
    "\u062c\u0627\u0631\u064a \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u0648\u0643\u0644\u0627\u0621...",
  agentsLoadFailed:
    "\u062a\u0639\u0630\u0631 \u062a\u062d\u0645\u064a\u0644 \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0648\u0643\u0644\u0627\u0621.",
  noResults:
    "\u0644\u0627 \u062a\u0648\u062c\u062f \u0646\u062a\u0627\u0626\u062c \u0645\u0637\u0627\u0628\u0642\u0629.",
  search:
    "\u0627\u0628\u062d\u062b \u0628\u0627\u0633\u0645 \u0627\u0644\u0648\u0643\u064a\u0644 \u0623\u0648 \u0627\u0644\u0639\u0645\u064a\u0644...",
  active:
    "\u0646\u0634\u0637",
  inactive:
    "\u0645\u062a\u0648\u0642\u0641",
  configured:
    "\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0645\u062d\u0641\u0648\u0638\u0629",
  unconfigured:
    "\u063a\u064a\u0631 \u0645\u0647\u064a\u0623",
  chooseAgent:
    "\u0627\u062e\u062a\u0631 \u0648\u0643\u064a\u0644\u0627\u064b",
  chooseDescription:
    "\u0627\u062e\u062a\u0631 \u0627\u0644\u0648\u0643\u064a\u0644 \u0627\u0644\u0630\u064a \u062a\u0631\u064a\u062f \u062a\u062e\u0635\u064a\u0635 \u0646\u0627\u0641\u0630\u0629 \u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0629 \u0627\u0644\u062e\u0627\u0635\u0629 \u0628\u0647.",
  identity:
    "\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0647\u0648\u064a\u0629",
  displayName:
    "\u0627\u0644\u0627\u0633\u0645 \u0627\u0644\u0638\u0627\u0647\u0631",
  greeting:
    "\u0631\u0633\u0627\u0644\u0629 \u0627\u0644\u062a\u0631\u062d\u064a\u0628",
  widgetStatus:
    "\u062d\u0627\u0644\u0629 \u0627\u0644\u0648\u064a\u062f\u062c\u062a",
  enable:
    "\u062a\u0641\u0639\u064a\u0644 \u0627\u0644\u0648\u064a\u062f\u062c\u062a",
  enabledHint:
    "\u0633\u064a\u0635\u0628\u062d \u0645\u062a\u0627\u062d\u064b\u0627 \u0644\u0644\u0645\u0648\u0627\u0642\u0639 \u0627\u0644\u0645\u0633\u0645\u0648\u062d \u0628\u0647\u0627 \u0628\u0639\u062f \u0627\u0644\u062d\u0641\u0638.",
  disabledHint:
    "\u0645\u0639\u0637\u0644 \u062d\u0627\u0644\u064a\u064b\u0627 \u0648\u0644\u0646 \u064a\u062a\u0645 \u0625\u0646\u0634\u0627\u0621 \u062c\u0644\u0633\u0627\u062a \u0639\u0627\u0645\u0629 \u0644\u0647.",
  appearance:
    "\u0627\u0644\u0645\u0638\u0647\u0631",
  light:
    "\u0641\u0627\u062a\u062d",
  dark:
    "\u062f\u0627\u0643\u0646",
  position:
    "\u0645\u0648\u0636\u0639 \u0627\u0644\u0646\u0627\u0641\u0630\u0629",
  right:
    "\u064a\u0645\u064a\u0646",
  left:
    "\u064a\u0633\u0627\u0631",
  colors:
    "\u0623\u0644\u0648\u0627\u0646 \u0627\u0644\u0648\u0627\u062c\u0647\u0629",
  primaryColor:
    "\u0627\u0644\u0644\u0648\u0646 \u0627\u0644\u0623\u0633\u0627\u0633\u064a",
  textColor:
    "\u0644\u0648\u0646 \u0627\u0644\u0646\u0635",
  launcherColor:
    "\u0644\u0648\u0646 \u0632\u0631 \u0627\u0644\u062a\u0634\u063a\u064a\u0644",
  headerColor:
    "\u0644\u0648\u0646 \u0627\u0644\u062a\u0631\u0648\u064a\u0633\u0629",
  userMessageColor:
    "\u0644\u0648\u0646 \u0631\u0633\u0627\u0644\u0629 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645",
  contrastHint:
    "\u064a\u062c\u0628 \u0623\u0646 \u064a\u062d\u0642\u0642 \u0644\u0648\u0646 \u0627\u0644\u0646\u0635 \u062a\u0628\u0627\u064a\u0646 WCAG AA \u0628\u0646\u0633\u0628\u0629 4.5:1 \u0645\u0639 \u0627\u0644\u0623\u0644\u0648\u0627\u0646 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645\u0629 \u062e\u0644\u0641\u0647.",
  invalidColor:
    "\u064a\u062c\u0628 \u0625\u062f\u062e\u0627\u0644 \u0643\u0644 \u0644\u0648\u0646 \u0628\u0635\u064a\u063a\u0629 #RRGGBB.",
  contrastFailed:
    "\u0641\u0634\u0644 \u0627\u0644\u062a\u0628\u0627\u064a\u0646",
  contrastPassed:
    "\u0627\u0644\u062a\u0628\u0627\u064a\u0646 \u0635\u0627\u0644\u062d",
  origins:
    "\u0627\u0644\u0646\u0637\u0627\u0642\u0627\u062a \u0627\u0644\u0645\u0633\u0645\u0648\u062d \u0628\u0647\u0627",
  originsHint:
    "\u0623\u0636\u0641 \u0646\u0637\u0627\u0642\u064b\u0627 \u0648\u0627\u062d\u062f\u064b\u0627 \u0641\u064a \u0643\u0644 \u0633\u0637\u0631\u060c \u0645\u062b\u0644 https://example.com. \u0627\u0644\u062d\u062f \u0627\u0644\u0623\u0642\u0635\u0649 50 \u0646\u0637\u0627\u0642\u064b\u0627.",
  publicId:
    "\u0645\u0639\u0631\u0641 \u0627\u0644\u0648\u064a\u062f\u062c\u062a \u0627\u0644\u0639\u0627\u0645",
  publicIdHint:
    "\u064a\u064f\u0646\u0634\u0623 \u0639\u0646\u062f \u0623\u0648\u0644 \u062d\u0641\u0638 \u0648\u064a\u0628\u0642\u0649 \u062b\u0627\u0628\u062a\u064b\u0627 \u0639\u0628\u0631 \u0627\u0644\u062a\u062d\u062f\u064a\u062b\u0627\u062a.",
  copyId:
    "\u0646\u0633\u062e \u0627\u0644\u0645\u0639\u0631\u0641",
  installTitle:
    "\u062a\u062b\u0628\u064a\u062a \u0627\u0644\u0648\u064a\u062f\u062c\u062a \u0641\u064a \u0645\u0648\u0642\u0639 \u0627\u0644\u0639\u0645\u064a\u0644",
  embedCode:
    "\u0643\u0648\u062f \u0627\u0644\u062a\u0636\u0645\u064a\u0646",
  copyEmbed:
    "\u0646\u0633\u062e \u0643\u0648\u062f \u0627\u0644\u062a\u0636\u0645\u064a\u0646",
  embedCopied:
    "\u062a\u0645 \u0646\u0633\u062e \u0643\u0648\u062f \u0627\u0644\u062a\u0636\u0645\u064a\u0646",
  embedReady:
    "\u0643\u0648\u062f \u0627\u0644\u062a\u0636\u0645\u064a\u0646 \u062c\u0627\u0647\u0632 \u0644\u0644\u0639\u0645\u064a\u0644.",
  embedNotReady:
    "\u0641\u0639\u0644 \u0627\u0644\u0648\u064a\u062f\u062c\u062a\u060c \u0623\u0636\u0641 \u0646\u0637\u0627\u0642\u064b\u0627 \u0645\u0633\u0645\u0648\u062d\u064b\u0627\u060c \u062b\u0645 \u0627\u062d\u0641\u0638 \u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a.",
  embedHint:
    "\u0636\u0639 \u0627\u0644\u0643\u0648\u062f \u0642\u0628\u0644 \u0648\u0633\u0645 </body> \u0641\u064a \u0645\u0648\u0642\u0639 \u0627\u0644\u0639\u0645\u064a\u0644.",
  copied:
    "\u062a\u0645 \u0627\u0644\u0646\u0633\u062e",
  notCreated:
    "\u0644\u0645 \u064a\u064f\u0646\u0634\u0623 \u0628\u0639\u062f",
  preview:
    "\u0645\u0639\u0627\u064a\u0646\u0629 \u0645\u0628\u0627\u0634\u0631\u0629",
  online:
    "\u0645\u062a\u0635\u0644",
  fallbackGreeting:
    "\u0645\u0631\u062d\u0628\u064b\u0627\u060c \u0643\u064a\u0641 \u064a\u0645\u0643\u0646\u0646\u064a \u0645\u0633\u0627\u0639\u062f\u062a\u0643 \u0627\u0644\u064a\u0648\u0645\u061f",
  composer:
    "\u0627\u0643\u062a\u0628 \u0631\u0633\u0627\u0644\u062a\u0643...",
  send:
    "\u0625\u0631\u0633\u0627\u0644",
  save:
    "\u062d\u0641\u0638 \u0627\u0644\u0625\u0639\u062f\u0627\u062f\u0627\u062a",
  reset:
    "\u0627\u0633\u062a\u0639\u0627\u062f\u0629 \u0622\u062e\u0631 \u0646\u0633\u062e\u0629",
  saving:
    "\u062c\u0627\u0631\u064a \u0627\u0644\u062d\u0641\u0638...",
  saved:
    "\u062a\u0645 \u062d\u0641\u0638 \u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0648\u064a\u062f\u062c\u062a \u0628\u0646\u062c\u0627\u062d.",
  notConfigured:
    "\u0644\u0645 \u064a\u062a\u0645 \u0625\u0639\u062f\u0627\u062f \u0627\u0644\u0648\u064a\u062f\u062c\u062a \u0644\u0647\u0630\u0627 \u0627\u0644\u0648\u0643\u064a\u0644 \u0628\u0639\u062f. \u0633\u064a\u0624\u062f\u064a \u0627\u0644\u062d\u0641\u0638 \u0627\u0644\u0623\u0648\u0644 \u0625\u0644\u0649 \u0625\u0646\u0634\u0627\u0621 \u0645\u0639\u0631\u0641 \u0639\u0627\u0645 \u062b\u0627\u0628\u062a.",
  settingsLoadFailed:
    "\u062a\u0639\u0630\u0631 \u062a\u062d\u0645\u064a\u0644 \u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0648\u064a\u062f\u062c\u062a.",
  settingsSaveFailed:
    "\u062a\u0639\u0630\u0631 \u062d\u0641\u0638 \u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0648\u064a\u062f\u062c\u062a.",
  unsaved:
    "\u0644\u062f\u064a\u0643 \u062a\u063a\u064a\u064a\u0631\u0627\u062a \u063a\u064a\u0631 \u0645\u062d\u0641\u0648\u0638\u0629. \u0647\u0644 \u062a\u0631\u064a\u062f \u0627\u0644\u0627\u0646\u062a\u0642\u0627\u0644 \u0625\u0644\u0649 \u0648\u0643\u064a\u0644 \u0622\u062e\u0631 \u0648\u0641\u0642\u062f\u0647\u0627\u061f",
  invalidOrigin:
    "\u064a\u062c\u0628 \u0623\u0646 \u064a\u062d\u062a\u0648\u064a \u0643\u0644 \u0646\u0637\u0627\u0642 \u0639\u0644\u0649 \u0639\u0646\u0648\u0627\u0646 HTTP \u0623\u0648 HTTPS \u0635\u0627\u0644\u062d.",
  insecureOrigin:
    "\u064a\u062c\u0628 \u0627\u0633\u062a\u062e\u062f\u0627\u0645 HTTPS \u062e\u0627\u0631\u062c localhost \u0648127.0.0.1.",
  duplicateOrigin:
    "\u0644\u0627 \u064a\u0645\u0643\u0646 \u062a\u0643\u0631\u0627\u0631 \u0627\u0644\u0646\u0637\u0627\u0642 \u0646\u0641\u0633\u0647.",
  tooManyOrigins:
    "\u0644\u0627 \u064a\u0645\u0643\u0646 \u0625\u0636\u0627\u0641\u0629 \u0623\u0643\u062b\u0631 \u0645\u0646 50 \u0646\u0637\u0627\u0642\u064b\u0627.",
  longOrigin:
    "\u064a\u062a\u062c\u0627\u0648\u0632 \u0623\u062d\u062f \u0627\u0644\u0646\u0637\u0627\u0642\u0627\u062a 255 \u062d\u0631\u0641\u064b\u0627.",
  retry:
    "\u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629",
} as const;

const widgetScriptUrl = (
  process.env.NEXT_PUBLIC_WIDGET_SCRIPT_URL ??
  "http://127.0.0.1:3000/widget/athka-widget.js"
).trim();

const widgetApiBaseUrl = (
  process.env.NEXT_PUBLIC_WIDGET_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const hexColorPattern =
  /^#[0-9A-Fa-f]{6}$/;

const colorFields = [
  {
    key: "primaryColor",
    label: copy.primaryColor,
  },
  {
    key: "textColor",
    label: copy.textColor,
  },
  {
    key: "launcherColor",
    label: copy.launcherColor,
  },
  {
    key: "headerColor",
    label: copy.headerColor,
  },
  {
    key: "userMessageColor",
    label: copy.userMessageColor,
  },
] as const;

const contrastBackgrounds = [
  {
    key: "primaryColor",
    label: copy.primaryColor,
  },
  {
    key: "launcherColor",
    label: copy.launcherColor,
  },
  {
    key: "headerColor",
    label: copy.headerColor,
  },
  {
    key: "userMessageColor",
    label: copy.userMessageColor,
  },
] as const;

function isRecord(
  value: unknown,
): value is Record<string, unknown> {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value)
  );
}

function agentKey(
  agent: AgentOption,
): string {
  return `${agent.tenant_id}::${agent.id}`;
}

function parseAgents(
  value: unknown,
): AgentOption[] {
  let rows: unknown = value;

  if (isRecord(value)) {
    rows =
      (
        Array.isArray(value.items)
          ? value.items
          : Array.isArray(value.agents)
            ? value.agents
            : value.data
      );
  }

  if (!Array.isArray(rows)) {
    return [];
  }

  return rows
    .flatMap((entry): AgentOption[] => {
      if (!isRecord(entry)) {
        return [];
      }

      const tenant = isRecord(entry.tenant)
        ? entry.tenant
        : null;

      if (
        typeof entry.id !== "string" ||
        typeof entry.tenant_id !== "string" ||
        typeof entry.name !== "string"
      ) {
        return [];
      }

      return [
        {
          id: entry.id,
          tenant_id: entry.tenant_id,
          name: entry.name,
          tenant_name:
            typeof entry.tenant_name === "string"
              ? entry.tenant_name
              : tenant &&
                  typeof tenant.name === "string"
                ? tenant.name
                : entry.tenant_id,
          is_active:
            entry.is_active === true,
        },
      ];
    })
    .sort((first, second) =>
      first.name.localeCompare(
        second.name,
        "ar",
      )
    );
}

function isWidgetTheme(
  value: unknown,
): value is WidgetTheme {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.primaryColor === "string" &&
    typeof value.textColor === "string" &&
    typeof value.launcherColor === "string" &&
    typeof value.headerColor === "string" &&
    typeof value.userMessageColor === "string" &&
    (
      value.position === "left" ||
      value.position === "right"
    ) &&
    (
      value.appearance === "light" ||
      value.appearance === "dark"
    )
  );
}

function isStringArray(
  value: unknown,
): value is string[] {
  return (
    Array.isArray(value) &&
    value.every(
      (entry) => typeof entry === "string",
    )
  );
}

function parseSettings(
  value: unknown,
): WidgetSettingsRecord | null {
  if (!isRecord(value)) {
    return null;
  }

  const tenantId = value.tenant_id;
  const agentId = value.agent_id;
  const publicWidgetId =
    value.public_widget_id;
  const isEnabled = value.is_enabled;
  const displayName = value.display_name;
  const greeting = value.greeting;
  const theme = value.theme;
  const allowedOrigins =
    value.allowed_origins;

  if (
    typeof tenantId !== "string" ||
    typeof agentId !== "string" ||
    typeof publicWidgetId !== "string" ||
    typeof isEnabled !== "boolean" ||
    !(
      displayName === null ||
      typeof displayName === "string"
    ) ||
    !(
      greeting === null ||
      typeof greeting === "string"
    ) ||
    !isWidgetTheme(theme) ||
    !isStringArray(allowedOrigins)
  ) {
    return null;
  }

  return {
    tenant_id: tenantId,
    agent_id: agentId,
    public_widget_id: publicWidgetId,
    is_enabled: isEnabled,
    display_name: displayName,
    greeting,
    theme: {
      ...theme,
    },
    allowed_origins: [
      ...allowedOrigins,
    ],
  };
}

function toPayload(
  settings: WidgetSettingsRecord,
): WidgetSettingsPutPayload {
  return {
    is_enabled: settings.is_enabled,
    display_name: settings.display_name,
    greeting: settings.greeting,
    theme: {
      ...settings.theme,
    },
    allowed_origins: [
      ...settings.allowed_origins,
    ],
  };
}

function clonePayload(
  payload: WidgetSettingsPutPayload,
): WidgetSettingsPutPayload {
  return {
    ...payload,
    theme: {
      ...payload.theme,
    },
    allowed_origins: [
      ...payload.allowed_origins,
    ],
  };
}

async function readBody(
  response: Response,
): Promise<unknown> {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function detailFromBody(
  body: unknown,
  fallback: string,
): string {
  if (
    isRecord(body) &&
    typeof body.detail === "string"
  ) {
    return body.detail;
  }

  if (typeof body === "string" && body) {
    return body;
  }

  return fallback;
}

function parseOrigins(
  value: string,
): OriginValidation {
  const rows = value
    .split(/\r?\n/)
    .map((row) => row.trim())
    .filter(Boolean);

  if (rows.length > 50) {
    return {
      origins: [],
      error: copy.tooManyOrigins,
    };
  }

  const origins: string[] = [];
  const seen = new Set<string>();

  for (const row of rows) {
    if (row.length > 255) {
      return {
        origins: [],
        error: copy.longOrigin,
      };
    }

    let url: URL;

    try {
      url = new URL(row);
    } catch {
      return {
        origins: [],
        error: copy.invalidOrigin,
      };
    }

    if (
      url.protocol !== "http:" &&
      url.protocol !== "https:"
    ) {
      return {
        origins: [],
        error: copy.invalidOrigin,
      };
    }

    const localHost =
      url.hostname === "localhost" ||
      url.hostname === "127.0.0.1" ||
      url.hostname === "::1";

    if (
      url.protocol === "http:" &&
      !localHost
    ) {
      return {
        origins: [],
        error: copy.insecureOrigin,
      };
    }

    const normalized = url.origin;

    if (seen.has(normalized)) {
      return {
        origins: [],
        error: copy.duplicateOrigin,
      };
    }

    seen.add(normalized);
    origins.push(normalized);
  }

  return {
    origins,
    error: null,
  };
}

function luminance(
  color: string,
): number | null {
  if (!hexColorPattern.test(color)) {
    return null;
  }

  const values = [
    color.slice(1, 3),
    color.slice(3, 5),
    color.slice(5, 7),
  ].map((channel) =>
    Number.parseInt(channel, 16) / 255
  );

  const linear = values.map((value) =>
    value <= 0.04045
      ? value / 12.92
      : ((value + 0.055) / 1.055) ** 2.4
  );

  return (
    0.2126 * linear[0] +
    0.7152 * linear[1] +
    0.0722 * linear[2]
  );
}

function contrastRatio(
  foreground: string,
  background: string,
): number {
  const first = luminance(foreground);
  const second = luminance(background);

  if (first === null || second === null) {
    return 0;
  }

  const lighter = Math.max(first, second);
  const darker = Math.min(first, second);

  return (
    (lighter + 0.05) /
    (darker + 0.05)
  );
}

export function WidgetSettingsView() {
  const [
    agents,
    setAgents,
  ] = useState<AgentOption[]>([]);

  const [
    selectedKey,
    setSelectedKey,
  ] = useState("");

  const [
    search,
    setSearch,
  ] = useState("");

  const [
    loadingAgents,
    setLoadingAgents,
  ] = useState(true);

  const [
    agentsError,
    setAgentsError,
  ] = useState<string | null>(null);

  const [
    loadingSettings,
    setLoadingSettings,
  ] = useState(false);

  const [
    saving,
    setSaving,
  ] = useState(false);

  const [
    configured,
    setConfigured,
  ] = useState(false);

  const [
    publicWidgetId,
    setPublicWidgetId,
  ] = useState<string | null>(null);

  const [
    draft,
    setDraft,
  ] =
    useState<WidgetSettingsPutPayload | null>(
      null,
    );

  const [
    baseline,
    setBaseline,
  ] =
    useState<WidgetSettingsPutPayload | null>(
      null,
    );

  const [
    originsText,
    setOriginsText,
  ] = useState("");

  const [
    baselineOriginsText,
    setBaselineOriginsText,
  ] = useState("");

  const [
    actionError,
    setActionError,
  ] = useState<string | null>(null);

  const [
    notice,
    setNotice,
  ] = useState<string | null>(null);

  const [
    copied,
    setCopied,
  ] = useState(false);

  const [
    copiedEmbed,
    setCopiedEmbed,
  ] = useState(false);



  const [
    pairingOrigin,
    setPairingOrigin,
  ] = useState("");

  const [
    pairingConnectorType,
    setPairingConnectorType,
  ] = useState<WidgetConnectorType>(
    "wordpress",
  );

  const [
    pairingResult,
    setPairingResult,
  ] = useState<WidgetConnectorPairing | null>(
    null,
  );

  const [
    pairingLoading,
    setPairingLoading,
  ] = useState(false);

  const [
    pairingError,
    setPairingError,
  ] = useState<string | null>(null);

  const [
    copiedPairing,
    setCopiedPairing,
  ] = useState(false);

  const [
    reloadVersion,
    setReloadVersion,
  ] = useState(0);

  const loadAgents = useCallback(
    async () => {
      setLoadingAgents(true);
      setAgentsError(null);

      try {
        const response = await fetch(
          "/api/agents",
          {
            cache: "no-store",
          },
        );

        const body = await readBody(response);

        if (!response.ok) {
          throw new Error(
            detailFromBody(
              body,
              copy.agentsLoadFailed,
            ),
          );
        }

        const parsed = parseAgents(body);

        setAgents(parsed);

        setSelectedKey((current) => {
          if (
            current &&
            parsed.some(
              (agent) =>
                agentKey(agent) === current,
            )
          ) {
            return current;
          }

          return parsed[0]
            ? agentKey(parsed[0])
            : "";
        });
      } catch (error) {
        setAgentsError(
          error instanceof Error
            ? error.message
            : copy.agentsLoadFailed,
        );
      } finally {
        setLoadingAgents(false);
      }
    },
    [],
  );

  useEffect(() => {
    const timeoutId = window.setTimeout(
      () => {
        void loadAgents();
      },
      0,
    );

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [loadAgents]);

  const selectedAgent = useMemo(
    () =>
      agents.find(
        (agent) =>
          agentKey(agent) === selectedKey,
      ) ?? null,
    [agents, selectedKey],
  );

  useEffect(() => {
    if (!selectedAgent) {
      const timeoutId = window.setTimeout(
        () => {
          setDraft(null);
          setBaseline(null);
          setOriginsText("");
          setBaselineOriginsText("");
          setPublicWidgetId(null);
          setConfigured(false);
        },
        0,
      );

      return () => {
        window.clearTimeout(timeoutId);
      };
    }

    const activeAgent = selectedAgent;
    let cancelled = false;

    async function loadSettings() {
      setLoadingSettings(true);
      setActionError(null);
      setNotice(null);
      setCopied(false);

      try {
        const response = await fetch(
          `/api/widget-settings/${
            encodeURIComponent(
              activeAgent.tenant_id,
            )
          }/${
            encodeURIComponent(
              activeAgent.id,
            )
          }`,
          {
            cache: "no-store",
          },
        );

        const body = await readBody(response);

        if (cancelled) {
          return;
        }

        if (response.status === 404) {
          const defaults =
            createDefaultWidgetPayload(
              activeAgent.name,
            );

          setDraft(clonePayload(defaults));
          setBaseline(clonePayload(defaults));
          setOriginsText("");
          setBaselineOriginsText("");
          setConfigured(false);
          setPublicWidgetId(null);
          setNotice(copy.notConfigured);
          return;
        }

        if (!response.ok) {
          throw new Error(
            detailFromBody(
              body,
              copy.settingsLoadFailed,
            ),
          );
        }

        const settings = parseSettings(body);

        if (!settings) {
          throw new Error(
            copy.settingsLoadFailed,
          );
        }

        const payload = toPayload(settings);
        const originValue =
          settings.allowed_origins.join("\n");

        setDraft(clonePayload(payload));
        setBaseline(clonePayload(payload));
        setOriginsText(originValue);
        setBaselineOriginsText(originValue);
        setConfigured(true);
        setPublicWidgetId(
          settings.public_widget_id,
        );
      } catch (error) {
        if (!cancelled) {
          setDraft(null);
          setBaseline(null);
          setActionError(
            error instanceof Error
              ? error.message
              : copy.settingsLoadFailed,
          );
        }
      } finally {
        if (!cancelled) {
          setLoadingSettings(false);
        }
      }
    }

    const timeoutId = window.setTimeout(
      () => {
        void loadSettings();
      },
      0,
    );

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [selectedAgent, reloadVersion]);

  const filteredAgents = useMemo(() => {
    const query = search
      .trim()
      .toLocaleLowerCase("ar");

    if (!query) {
      return agents;
    }

    return agents.filter((agent) =>
      [
        agent.name,
        agent.tenant_name,
        agent.id,
        agent.tenant_id,
      ].some((value) =>
        value
          .toLocaleLowerCase("ar")
          .includes(query)
      )
    );
  }, [agents, search]);

  const originValidation = useMemo(
    () => parseOrigins(originsText),
    [originsText],
  );

  const invalidColors = useMemo(
    () =>
      draft
        ? colorFields.some(
            ({ key }) =>
              !hexColorPattern.test(
                draft.theme[key],
              ),
          )
        : false,
    [draft],
  );

  const contrastChecks = useMemo(
    () =>
      draft
        ? contrastBackgrounds.map(
            ({ key, label }) => ({
              key,
              label,
              ratio: contrastRatio(
                draft.theme.textColor,
                draft.theme[key],
              ),
            }),
          )
        : [],
    [draft],
  );

  const contrastFailed =
    contrastChecks.some(
      ({ ratio }) => ratio < 4.5,
    );

  const effectivePairingOrigin =
    originValidation.origins.includes(
      pairingOrigin,
    )
      ? pairingOrigin
      : (
          originValidation.origins[0]
          ?? ""
        );

  useEffect(() => {
    const timeoutId = window.setTimeout(
      () => {
        setPairingOrigin("");
        setPairingConnectorType("wordpress");
        setPairingResult(null);
        setPairingError(null);
        setCopiedPairing(false);
      },
      0,
    );

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [
    selectedAgent?.tenant_id,
    selectedAgent?.id,
  ]);

  const dirty = useMemo(
    () =>
      draft !== null &&
      baseline !== null &&
      (
        JSON.stringify(draft) !==
          JSON.stringify(baseline) ||
        originsText !== baselineOriginsText
      ),
    [
      draft,
      baseline,
      originsText,
      baselineOriginsText,
    ],
  );

  const canSave =
    selectedAgent !== null &&
    draft !== null &&
    !loadingSettings &&
    !saving &&
    !invalidColors &&
    !contrastFailed &&
    originValidation.error === null &&
    (
      !configured ||
      dirty
    );

  function selectAgent(
    nextKey: string,
  ) {
    if (nextKey === selectedKey) {
      return;
    }

    if (
      dirty &&
      !window.confirm(copy.unsaved)
    ) {
      return;
    }

    setSelectedKey(nextKey);
  }

  function updateDraft(
    update:
      Partial<WidgetSettingsPutPayload>,
  ) {
    setDraft((current) =>
      current
        ? {
            ...current,
            ...update,
          }
        : current
    );

    setActionError(null);
    setNotice(null);
  }

  function updateTheme<
    Key extends keyof WidgetTheme,
  >(
    key: Key,
    value: WidgetTheme[Key],
  ) {
    setDraft((current) =>
      current
        ? {
            ...current,
            theme: {
              ...current.theme,
              [key]: value,
            },
          }
        : current
    );

    setActionError(null);
    setNotice(null);
  }

  async function saveSettings() {
    if (
      !selectedAgent ||
      !draft ||
      originValidation.error ||
      invalidColors ||
      contrastFailed
    ) {
      return;
    }

    const payload:
      WidgetSettingsPutPayload = {
        is_enabled: draft.is_enabled,
        display_name:
          draft.display_name?.trim() ||
          null,
        greeting:
          draft.greeting?.trim() ||
          null,
        theme: {
          primaryColor:
            draft.theme.primaryColor
              .toUpperCase(),
          textColor:
            draft.theme.textColor
              .toUpperCase(),
          launcherColor:
            draft.theme.launcherColor
              .toUpperCase(),
          headerColor:
            draft.theme.headerColor
              .toUpperCase(),
          userMessageColor:
            draft.theme.userMessageColor
              .toUpperCase(),
          position: draft.theme.position,
          appearance:
            draft.theme.appearance,
        },
        allowed_origins:
          originValidation.origins,
      };

    setSaving(true);
    setActionError(null);
    setNotice(null);

    try {
      const response = await fetch(
        `/api/widget-settings/${
          encodeURIComponent(
            selectedAgent.tenant_id,
          )
        }/${
          encodeURIComponent(
            selectedAgent.id,
          )
        }`,
        {
          method: "PUT",
          cache: "no-store",
          headers: {
            "Content-Type":
              "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(payload),
        },
      );

      const body = await readBody(response);

      if (!response.ok) {
        throw new Error(
          detailFromBody(
            body,
            copy.settingsSaveFailed,
          ),
        );
      }

      const settings = parseSettings(body);

      if (!settings) {
        throw new Error(
          copy.settingsSaveFailed,
        );
      }

      const savedPayload =
        toPayload(settings);

      const originValue =
        settings.allowed_origins.join("\n");

      setDraft(
        clonePayload(savedPayload),
      );

      setBaseline(
        clonePayload(savedPayload),
      );

      setOriginsText(originValue);
      setBaselineOriginsText(originValue);
      setConfigured(true);
      setPublicWidgetId(
        settings.public_widget_id,
      );
      setNotice(copy.saved);
    } catch (error) {
      setActionError(
        error instanceof Error
          ? error.message
          : copy.settingsSaveFailed,
      );
    } finally {
      setSaving(false);
    }
  }

  function resetSettings() {
    if (!baseline) {
      return;
    }

    setDraft(clonePayload(baseline));
    setOriginsText(
      baselineOriginsText,
    );
    setActionError(null);
    setNotice(null);
  }

  function reloadSettings() {
    if (
      dirty &&
      !window.confirm(copy.unsaved)
    ) {
      return;
    }

    setReloadVersion(
      (current) => current + 1,
    );
  }

  async function copyWidgetId() {
    if (!publicWidgetId) {
      return;
    }

    try {
      await navigator.clipboard.writeText(
        publicWidgetId,
      );

      setCopied(true);

      window.setTimeout(
        () => setCopied(false),
        1800,
      );
    } catch {
      setCopied(false);
    }
  }

  async function createPairingCode() {
    if (
      !selectedAgent
      || !effectivePairingOrigin
      || !embedReady
    ) {
      return;
    }

    setPairingLoading(true);
    setPairingError(null);
    setPairingResult(null);
    setCopiedPairing(false);

    try {
      const response = await fetch(
        `/api/widget-settings/${
          encodeURIComponent(
            selectedAgent.tenant_id,
          )
        }/${
          encodeURIComponent(
            selectedAgent.id,
          )
        }/pairings`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            origin:
              effectivePairingOrigin,
            connector_type:
              pairingConnectorType,
          }),
        },
      );

      const body = await readBody(response);

      if (!response.ok) {
        throw new Error(
          detailFromBody(
            body,
            "تعذر إنشاء رمز الربط.",
          ),
        );
      }

      if (
        body === null
        || typeof body !== "object"
        || Array.isArray(body)
      ) {
        throw new Error(
          "استجابة رمز الربط غير صالحة.",
        );
      }

      const value =
        body as Record<string, unknown>;

      if (
        typeof value.pairing_id !== "string"
        || typeof value.pairing_code !== "string"
        || typeof value.origin !== "string"
        || (
          value.connector_type
            !== "wordpress"
          && value.connector_type
            !== "react_next"
          && value.connector_type
            !== "managed"
          && value.connector_type
            !== "custom"
        )
        || typeof value.expires_at !== "string"
        || typeof value.expires_in !== "number"
      ) {
        throw new Error(
          "استجابة رمز الربط غير مكتملة.",
        );
      }

      setPairingResult({
        pairing_id: value.pairing_id,
        pairing_code:
          value.pairing_code,
        origin: value.origin,
        connector_type:
          value.connector_type,
        expires_at: value.expires_at,
        expires_in: value.expires_in,
      });
    } catch (error) {
      setPairingError(
        error instanceof Error
          ? error.message
          : "تعذر إنشاء رمز الربط.",
      );
    } finally {
      setPairingLoading(false);
    }
  }

  async function copyPairingCode() {
    if (!pairingResult) {
      return;
    }

    try {
      await navigator.clipboard.writeText(
        pairingResult.pairing_code,
      );

      setCopiedPairing(true);

      window.setTimeout(
        () => setCopiedPairing(false),
        1800,
      );
    } catch {
      setCopiedPairing(false);
    }
  }

  const embedReady =
    Boolean(publicWidgetId) &&
    configured &&
    baseline?.is_enabled === true &&
    baseline.allowed_origins.length > 0 &&
    !dirty;

  const embedCode = useMemo(
    () =>
      publicWidgetId
        ? [
            "<script",
            `  src="${widgetScriptUrl}"`,
            `  data-widget-id="${publicWidgetId}"`,
            `  data-api-base="${widgetApiBaseUrl}"`,
            "  defer",
            "></script>",
          ].join("\\n")
        : "",
    [publicWidgetId],
  );

  async function copyEmbedCode() {
    if (!embedReady || !embedCode) {
      return;
    }

    try {
      await navigator.clipboard.writeText(
        embedCode,
      );

      setCopiedEmbed(true);

      window.setTimeout(
        () => setCopiedEmbed(false),
        1800,
      );
    } catch {
      setCopiedEmbed(false);
    }
  }

  const previewName =
    draft?.display_name?.trim() ||
    selectedAgent?.name ||
    "Athkachatbots";

  const previewGreeting =
    draft?.greeting?.trim() ||
    copy.fallbackGreeting;

  return (
    <main
      className="widget-settings-page"
      dir="rtl"
    >
      <header className="widget-settings-hero">
        <div>
          <span className="widget-settings-hero__eyebrow">
            <MessageCircle aria-hidden="true" />
            Athkachatbots Widget
          </span>

          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>

        <button
          className="widget-settings-button widget-settings-button--secondary"
          type="button"
          onClick={() => void loadAgents()}
          disabled={loadingAgents}
        >
          {loadingAgents ? (
            <Loader2
              className="widget-settings-spin"
              aria-hidden="true"
            />
          ) : (
            <RefreshCw aria-hidden="true" />
          )}

          {copy.refreshAgents}
        </button>
      </header>

      <div className="widget-settings-layout">
        <aside className="widget-settings-agents">
          <div className="widget-settings-panel-heading">
            <div>
              <span>
                {agents.length}
              </span>
              <h2>{copy.chooseAgent}</h2>
            </div>

            <Bot aria-hidden="true" />
          </div>

          <label className="widget-settings-search">
            <Search aria-hidden="true" />

            <input
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value,
                )
              }
              placeholder={copy.search}
              aria-label={copy.search}
            />
          </label>

          <div className="widget-settings-agent-list">
            {loadingAgents ? (
              <div className="widget-settings-empty">
                <Loader2
                  className="widget-settings-spin"
                  aria-hidden="true"
                />
                <p>{copy.loadingAgents}</p>
              </div>
            ) : agentsError ? (
              <div className="widget-settings-empty widget-settings-empty--error">
                <p>{agentsError}</p>

                <button
                  type="button"
                  onClick={() =>
                    void loadAgents()
                  }
                >
                  {copy.retry}
                </button>
              </div>
            ) : filteredAgents.length === 0 ? (
              <div className="widget-settings-empty">
                <Search aria-hidden="true" />
                <p>{copy.noResults}</p>
              </div>
            ) : (
              filteredAgents.map((agent) => {
                const key = agentKey(agent);
                const selected =
                  key === selectedKey;

                return (
                  <button
                    key={key}
                    type="button"
                    className={
                      "widget-settings-agent-card"
                      + (
                        selected
                          ? " is-selected"
                          : ""
                      )
                    }
                    aria-pressed={selected}
                    onClick={() =>
                      selectAgent(key)
                    }
                  >
                    <span className="widget-settings-agent-card__icon">
                      <Bot aria-hidden="true" />
                    </span>

                    <span className="widget-settings-agent-card__content">
                      <strong>{agent.name}</strong>
                      <small>
                        {agent.tenant_name}
                      </small>

                      <span
                        className={
                          "widget-settings-status-dot"
                          + (
                            agent.is_active
                              ? " is-active"
                              : ""
                          )
                        }
                      >
                        {agent.is_active
                          ? copy.active
                          : copy.inactive}
                      </span>
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </aside>

        <section className="widget-settings-editor">
          {!selectedAgent ? (
            <div className="widget-settings-placeholder">
              <Bot aria-hidden="true" />
              <h2>{copy.chooseAgent}</h2>
              <p>{copy.chooseDescription}</p>
            </div>
          ) : loadingSettings ? (
            <div className="widget-settings-placeholder">
              <Loader2
                className="widget-settings-spin"
                aria-hidden="true"
              />
              <p>
                {copy.settingsLoadFailed
                  .replace(
                    "\u062a\u0639\u0630\u0631",
                    "\u062c\u0627\u0631\u064a",
                  )}
              </p>
            </div>
          ) : !draft ? (
            <div className="widget-settings-placeholder widget-settings-placeholder--error">
              <ShieldCheck aria-hidden="true" />
              <p>
                {actionError ??
                  copy.settingsLoadFailed}
              </p>

              <button
                type="button"
                onClick={reloadSettings}
              >
                {copy.retry}
              </button>
            </div>
          ) : (
            <>
              <div className="widget-settings-selected">
                <div>
                  <span>
                    {selectedAgent.tenant_name}
                  </span>

                  <h2>{selectedAgent.name}</h2>

                  <small>
                    {selectedAgent.id}
                  </small>
                </div>

                <div className="widget-settings-selected__badges">
                  <span
                    className={
                      configured
                        ? "is-configured"
                        : "is-new"
                    }
                  >
                    {configured
                      ? copy.configured
                      : copy.unconfigured}
                  </span>

                  <button
                    type="button"
                    title={copy.refreshAgents}
                    onClick={reloadSettings}
                  >
                    <RefreshCw
                      aria-hidden="true"
                    />
                  </button>
                </div>
              </div>

              {notice ? (
                <div
                  className="widget-settings-notice"
                  role="status"
                >
                  <Check aria-hidden="true" />
                  <span>{notice}</span>
                </div>
              ) : null}

              {actionError ? (
                <div
                  className="widget-settings-notice widget-settings-notice--error"
                  role="alert"
                >
                  <ShieldCheck
                    aria-hidden="true"
                  />
                  <span>{actionError}</span>
                </div>
              ) : null}

              <section className="widget-settings-card">
                <div className="widget-settings-card__title">
                  <MessageCircle
                    aria-hidden="true"
                  />
                  <h3>{copy.identity}</h3>
                </div>

                <div className="widget-settings-fields">
                  <label>
                    <span>{copy.displayName}</span>
                    <input
                      value={
                        draft.display_name ??
                        ""
                      }
                      maxLength={255}
                      onChange={(event) =>
                        updateDraft({
                          display_name:
                            event.target.value,
                        })
                      }
                    />
                    <small>
                      {
                        (
                          draft.display_name ??
                          ""
                        ).length
                      }
                      /255
                    </small>
                  </label>

                  <label>
                    <span>{copy.greeting}</span>
                    <textarea
                      value={
                        draft.greeting ?? ""
                      }
                      maxLength={500}
                      rows={4}
                      onChange={(event) =>
                        updateDraft({
                          greeting:
                            event.target.value,
                        })
                      }
                    />
                    <small>
                      {
                        (
                          draft.greeting ?? ""
                        ).length
                      }
                      /500
                    </small>
                  </label>
                </div>
              </section>

              <section className="widget-settings-card">
                <div className="widget-settings-card__title">
                  <Power aria-hidden="true" />
                  <h3>{copy.widgetStatus}</h3>
                </div>

                <label className="widget-settings-toggle-row">
                  <span>
                    <strong>{copy.enable}</strong>
                    <small>
                      {draft.is_enabled
                        ? copy.enabledHint
                        : copy.disabledHint}
                    </small>
                  </span>

                  <input
                    type="checkbox"
                    checked={draft.is_enabled}
                    onChange={(event) =>
                      updateDraft({
                        is_enabled:
                          event.target.checked,
                      })
                    }
                  />

                  <span
                    className="widget-settings-switch"
                    aria-hidden="true"
                  >
                    <span />
                  </span>
                </label>

                <div className="widget-settings-segment-grid">
                  <fieldset>
                    <legend>
                      {copy.appearance}
                    </legend>

                    <div className="widget-settings-segments">
                      {(
                        [
                          ["light", copy.light],
                          ["dark", copy.dark],
                        ] as const
                      ).map(
                        ([value, label]) => (
                          <button
                            key={value}
                            type="button"
                            className={
                              draft.theme
                                .appearance ===
                              value
                                ? "is-selected"
                                : ""
                            }
                            onClick={() =>
                              updateTheme(
                                "appearance",
                                value,
                              )
                            }
                          >
                            {label}
                          </button>
                        ),
                      )}
                    </div>
                  </fieldset>

                  <fieldset>
                    <legend>
                      {copy.position}
                    </legend>

                    <div className="widget-settings-segments">
                      {(
                        [
                          ["right", copy.right],
                          ["left", copy.left],
                        ] as const
                      ).map(
                        ([value, label]) => (
                          <button
                            key={value}
                            type="button"
                            className={
                              draft.theme
                                .position ===
                              value
                                ? "is-selected"
                                : ""
                            }
                            onClick={() =>
                              updateTheme(
                                "position",
                                value,
                              )
                            }
                          >
                            {label}
                          </button>
                        ),
                      )}
                    </div>
                  </fieldset>
                </div>
              </section>

              <section className="widget-settings-card">
                <div className="widget-settings-card__title">
                  <Paintbrush
                    aria-hidden="true"
                  />
                  <h3>{copy.colors}</h3>
                </div>

                <div className="widget-settings-color-grid">
                  {colorFields.map(
                    ({ key, label }) => {
                      const value =
                        draft.theme[key];

                      return (
                        <label key={key}>
                          <span>{label}</span>

                          <div className="widget-settings-color-input">
                            <input
                              type="color"
                              value={
                                hexColorPattern
                                  .test(value)
                                  ? value
                                  : "#000000"
                              }
                              onChange={(
                                event,
                              ) =>
                                updateTheme(
                                  key,
                                  event.target
                                    .value
                                    .toUpperCase(),
                                )
                              }
                            />

                            <input
                              value={value}
                              maxLength={7}
                              dir="ltr"
                              onChange={(
                                event,
                              ) =>
                                updateTheme(
                                  key,
                                  event.target
                                    .value
                                    .toUpperCase(),
                                )
                              }
                            />
                          </div>
                        </label>
                      );
                    },
                  )}
                </div>

                <div
                  className={
                    "widget-settings-contrast"
                    + (
                      invalidColors ||
                      contrastFailed
                        ? " is-invalid"
                        : " is-valid"
                    )
                  }
                >
                  <div>
                    {invalidColors ||
                    contrastFailed ? (
                      <ShieldCheck
                        aria-hidden="true"
                      />
                    ) : (
                      <Check
                        aria-hidden="true"
                      />
                    )}

                    <strong>
                      {invalidColors ||
                      contrastFailed
                        ? copy.contrastFailed
                        : copy.contrastPassed}
                    </strong>
                  </div>

                  <p>
                    {invalidColors
                      ? copy.invalidColor
                      : copy.contrastHint}
                  </p>

                  {!invalidColors ? (
                    <ul>
                      {contrastChecks.map(
                        ({
                          key,
                          label,
                          ratio,
                        }) => (
                          <li key={key}>
                            <span>{label}</span>
                            <strong>
                              {ratio.toFixed(2)}
                              :1
                            </strong>
                          </li>
                        ),
                      )}
                    </ul>
                  ) : null}
                </div>
              </section>

          <section className="widget-settings-card">
            <div className="widget-settings-card__title">
              <Globe2 aria-hidden="true" />
              <h3>مواقع تثبيت الـChatbot</h3>
            </div>

            <p className="widget-settings-help">
              أضف المواقع التي تريد أن يظهر فيها هذا الـChatbot.
              يكفي إدخال عنوان الموقع، ولا تحتاج إلى كتابة مسار صفحة.
            </p>

            <form
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                marginTop: 14,
              }}
              onSubmit={(event) => {
                event.preventDefault();

                const form = event.currentTarget;
                const formData = new FormData(form);

                const raw = String(
                  formData.get("site") ?? "",
                ).trim();

                if (!raw) {
                  return;
                }

                try {
                  const candidate =
                    /^[a-z][a-z0-9+.-]*:\/\//i.test(raw)
                      ? raw
                      : `https://${raw}`;

                  const parsed = new URL(candidate);

                  if (
                    parsed.protocol !== "https:" &&
                    parsed.protocol !== "http:"
                  ) {
                    throw new Error(
                      "Unsupported protocol",
                    );
                  }

                  const origin = parsed.origin;

                  const currentOrigins =
                    originsText
                      .split(/\r?\n/)
                      .map((value) =>
                        value.trim()
                      )
                      .filter(Boolean);

                  if (
                    !currentOrigins.includes(origin)
                  ) {
                    setOriginsText(
                      [
                        ...currentOrigins,
                        origin,
                      ].join("\n"),
                    );
                  }

                  setActionError(null);
                  setNotice(null);

                  form.reset();
                } catch {
                  setActionError(
                    "أدخل عنوان موقع صالحًا مثل example.com",
                  );
                }
              }}
            >
              <input
                name="site"
                type="text"
                dir="ltr"
                autoComplete="url"
                placeholder="example.com"
                style={{
                  flex: "1 1 auto",
                  minWidth: 0,
                  height: 46,
                  border:
                    "1px solid rgba(148,163,184,.22)",
                  borderRadius: 12,
                  padding: "0 14px",
                  color: "inherit",
                  background:
                    "rgba(10,12,20,.62)",
                  outline: 0,
                }}
              />

              <button
                type="submit"
                className="widget-settings-button widget-settings-button--primary"
              >
                + إضافة الموقع
              </button>
            </form>

            <div
              style={{
                display: "grid",
                gap: 10,
                marginTop: 16,
              }}
            >
              {originValidation.origins.length === 0 ? (
                <div className="widget-settings-notice">
                  لم تتم إضافة أي موقع بعد.
                </div>
              ) : (
                originValidation.origins.map(
                  (origin) => {
                    let hostname = origin;

                    try {
                      hostname =
                        new URL(origin).hostname;
                    } catch {
                      // Keep the origin as fallback.
                    }

                    return (
                      <div
                        key={origin}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent:
                            "space-between",
                          gap: 14,
                          border:
                            "1px solid rgba(148,163,184,.16)",
                          borderRadius: 14,
                          padding: "13px 14px",
                          background:
                            "rgba(255,255,255,.025)",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 11,
                            minWidth: 0,
                          }}
                        >
                          <Globe2
                            aria-hidden="true"
                            style={{
                              width: 20,
                              height: 20,
                              flex: "0 0 auto",
                            }}
                          />

                          <div
                            style={{
                              minWidth: 0,
                            }}
                          >
                            <strong
                              style={{
                                display: "block",
                              }}
                            >
                              {hostname}
                            </strong>

                            <small
                              dir="ltr"
                              style={{
                                display: "block",
                                marginTop: 4,
                                opacity: 0.72,
                                overflow: "hidden",
                                textOverflow:
                                  "ellipsis",
                                whiteSpace:
                                  "nowrap",
                              }}
                            >
                              {origin}
                            </small>
                          </div>
                        </div>

                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 10,
                          }}
                        >
                          <span
                            style={{
                              color: "#6FF1C2",
                              fontSize: 12,
                            }}
                          >
                            ● مسموح
                          </span>

                          <button
                            type="button"
                            className="widget-settings-button widget-settings-button--secondary"
                            onClick={() => {
                              const remaining =
                                originValidation
                                  .origins
                                  .filter(
                                    (item) =>
                                      item !== origin,
                                  );

                              setOriginsText(
                                remaining.join(
                                  "\n",
                                ),
                              );

                              setActionError(
                                null,
                              );
                              setNotice(null);
                            }}
                          >
                            إزالة
                          </button>
                        </div>
                      </div>
                    );
                  },
                )
              )}
            </div>

            <p className="widget-settings-help">
              تستخدم Athkachatbots هذه المواقع لمنع تشغيل
              الـChatbot على مواقع غير مصرح بها.
            </p>

            {originValidation.error ? (
              <p className="widget-settings-field-error">
                {originValidation.error}
              </p>
            ) : null}
          </section>

                    <section className="widget-settings-card">
            <div className="widget-settings-card__title">
              <ShieldCheck aria-hidden="true" />
              <h3>ربط الموقع</h3>
            </div>

            <div
              className={
                "widget-settings-embed-status"
                + (
                  embedReady
                    ? " is-ready"
                    : " is-blocked"
                )
              }
            >
              {embedReady ? (
                <Check aria-hidden="true" />
              ) : (
                <ShieldCheck aria-hidden="true" />
              )}

              <span>
                {embedReady
                  ? "الـChatbot جاهز للربط بالموقع"
                  : "احفظ الإعدادات وفعّل الـChatbot وأضف موقعًا"}
              </span>
            </div>

            {embedReady ? (
              <div
                className="widget-settings-install widget-settings-installation-code-live"
                style={{
                  marginTop: 20,
                  marginBottom: 22,
                }}
              >
                <div className="widget-settings-card__title">
                  <Clipboard aria-hidden="true" />

                  <h3>
                    كود تثبيت Chatbot
                  </h3>
                </div>

                <p className="widget-settings-help">
                  انسخ هذا الكود وضعه قبل وسم
                  {" </body> "}
                  في موقع العميل.
                </p>

                <label className="widget-settings-embed-code">
                  <span>
                    كود التثبيت
                  </span>

                  <textarea
                    dir="ltr"
                    rows={7}
                    readOnly
                    value={embedCode}
                  />
                </label>

                <button
                  className="widget-settings-button widget-settings-button--primary"
                  type="button"
                  disabled={!embedReady}
                  onClick={() =>
                    void copyEmbedCode()
                  }
                >
                  {copiedEmbed ? (
                    <Check aria-hidden="true" />
                  ) : (
                    <Clipboard aria-hidden="true" />
                  )}

                  {copiedEmbed
                    ? "تم نسخ كود التثبيت"
                    : "نسخ كود التثبيت"}
                </button>

                <div
                  className="widget-settings-embed-status is-ready"
                >
                  <Check aria-hidden="true" />

                  <span>
                    كود التثبيت جاهز.
                  </span>
                </div>
              </div>
            ) : null}


            <p className="widget-settings-help">
              اختر الموقع وطريقة التكامل، ثم أنشئ
              رمز ربط مؤقت يستخدمه Athkachatbots
              Connector مرة واحدة فقط أثناء التثبيت.
            </p>

            {embedReady ? (
              <div
                style={{
                  display: "grid",
                  gap: 18,
                  marginTop: 20,
                }}
              >
                <label
                  style={{
                    display: "grid",
                    gap: 8,
                  }}
                >
                  <span
                    style={{
                      fontWeight: 700,
                    }}
                  >
                    الموقع
                  </span>

                  <select
                    value={
                      effectivePairingOrigin
                    }
                    onChange={(event) => {
                      setPairingOrigin(
                        event.target.value,
                      );
                      setPairingResult(null);
                      setPairingError(null);
                    }}
                    style={{
                      width: "100%",
                      minHeight: 44,
                      borderRadius: 10,
                      padding: "0 12px",
                    }}
                  >
                    {originValidation.origins.map(
                      (origin) => (
                        <option
                          key={origin}
                          value={origin}
                        >
                          {origin}
                        </option>
                      ),
                    )}
                  </select>
                </label>

                <div>
                  <span
                    style={{
                      display: "block",
                      marginBottom: 10,
                      fontWeight: 700,
                    }}
                  >
                    طريقة الربط
                  </span>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns:
                        "repeat(auto-fit, minmax(150px, 1fr))",
                      gap: 10,
                    }}
                  >
                    {[
                      {
                        value: "wordpress",
                        label: "WordPress",
                      },
                      {
                        value: "react_next",
                        label: "React / Next.js",
                      },
                      {
                        value: "custom",
                        label: "موقع مخصص",
                      },
                    ].map((option) => (
                      <button
                        key={option.value}
                        type="button"
                        className={
                          "widget-settings-button "
                          + (
                            pairingConnectorType
                              === option.value
                              ? "widget-settings-button--primary"
                              : "widget-settings-button--secondary"
                          )
                        }
                        onClick={() => {
                          setPairingConnectorType(
                            option.value as WidgetConnectorType,
                          );
                          setPairingResult(null);
                          setPairingError(null);
                        }}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  className={
                    "widget-settings-button "
                    + "widget-settings-button--primary"
                  }
                  disabled={pairingLoading}
                  onClick={() =>
                    void createPairingCode()
                  }
                >
                  {pairingLoading ? (
                    <Loader2
                      className="widget-settings-spin"
                      aria-hidden="true"
                    />
                  ) : (
                    <ShieldCheck
                      aria-hidden="true"
                    />
                  )}

                  {pairingLoading
                    ? "جاري إنشاء رمز الربط..."
                    : "إنشاء رمز الربط"}
                </button>

                {pairingError ? (
                  <p className="widget-settings-field-error">
                    {pairingError}
                  </p>
                ) : null}

                {pairingResult ? (
                  <div
                    style={{
                      display: "grid",
                      gap: 12,
                      padding: 16,
                      border:
                        "1px solid rgba(34,197,94,.28)",
                      borderRadius: 14,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        fontWeight: 700,
                      }}
                    >
                      <Check aria-hidden="true" />
                      رمز الربط جاهز
                    </div>

                    <div
                      className="widget-settings-public-id"
                    >
                      <code
                        dir="ltr"
                        style={{
                          fontSize: 16,
                          letterSpacing: 1,
                        }}
                      >
                        {
                          pairingResult.pairing_code
                        }
                      </code>

                      <button
                        type="button"
                        onClick={() =>
                          void copyPairingCode()
                        }
                      >
                        {copiedPairing ? (
                          <Check
                            aria-hidden="true"
                          />
                        ) : (
                          <Clipboard
                            aria-hidden="true"
                          />
                        )}

                        {copiedPairing
                          ? "تم النسخ"
                          : "نسخ الرمز"}
                      </button>
                    </div>

                    <p className="widget-settings-help">
                      الرمز صالح لمدة{" "}
                      {Math.ceil(
                        pairingResult.expires_in
                          / 60,
                      )}{" "}
                      دقائق ويستخدم مرة واحدة فقط.
                    </p>

                    <p className="widget-settings-help">
                      الموقع:{" "}
                      <strong dir="ltr">
                        {pairingResult.origin}
                      </strong>
                    </p>
                  </div>
                ) : null}
              </div>
            ) : null}

            <details
              style={{
                marginTop: 18,
                paddingTop: 14,
                borderTop:
                  "1px solid rgba(148,163,184,.14)",
              }}
            >
              <summary
                style={{
                  cursor: "pointer",
                  fontWeight: 700,
                }}
              >
                معلومات تقنية متقدمة
              </summary>

              <div
                style={{
                  marginTop: 14,
                }}
              >
                <span
                  style={{
                    display: "block",
                    marginBottom: 8,
                    opacity: 0.72,
                    fontSize: 12,
                  }}
                >
                  معرف الـWidget العام
                </span>

                <div className="widget-settings-public-id">
                  <code dir="ltr">
                    {publicWidgetId ??
                      copy.notCreated}
                  </code>

                  <button
                    type="button"
                    disabled={!publicWidgetId}
                    onClick={() =>
                      void copyWidgetId()
                    }
                  >
                    {copied ? (
                      <Check
                        aria-hidden="true"
                      />
                    ) : (
                      <Clipboard
                        aria-hidden="true"
                      />
                    )}

                    {copied
                      ? copy.copied
                      : copy.copyId}
                  </button>
                </div>
              </div>
            </details>
          </section>

          <footer className="widget-settings-actions">
                <button
                  className="widget-settings-button widget-settings-button--secondary"
                  type="button"
                  disabled={!dirty || saving}
                  onClick={resetSettings}
                >
                  <Undo2 aria-hidden="true" />
                  {copy.reset}
                </button>

                <button
                  className="widget-settings-button widget-settings-button--primary"
                  type="button"
                  disabled={!canSave}
                  onClick={() =>
                    void saveSettings()
                  }
                >
                  {saving ? (
                    <Loader2
                      className="widget-settings-spin"
                      aria-hidden="true"
                    />
                  ) : (
                    <Save aria-hidden="true" />
                  )}

                  {saving
                    ? copy.saving
                    : copy.save}
                </button>
              </footer>
            </>
          )}
        </section>

        <aside className="widget-settings-preview">
          <div className="widget-settings-preview__heading">
            <span>
              <MessageCircle
                aria-hidden="true"
              />
              {copy.preview}
            </span>

            <small>
              {draft?.theme.appearance ===
              "dark"
                ? copy.dark
                : copy.light}
            </small>
          </div>

          {selectedAgent && draft ? (
            <div
              className={
                "widget-settings-preview-stage"
                + (
                  draft.theme.appearance ===
                  "dark"
                    ? " is-dark"
                    : " is-light"
                )
                + (
                  draft.theme.position ===
                  "left"
                    ? " is-left"
                    : " is-right"
                )
              }
            >
              <div className="widget-settings-preview-browser">
                <span />
                <span />
                <span />
              </div>

              <LiveWidgetPreview
                publicWidgetId={
                  publicWidgetId
                }
                displayName={previewName}
                greeting={previewGreeting}
                theme={draft.theme}
                isEnabled={draft.is_enabled}
              />
              <button
                type="button"
                className="widget-settings-launcher"
                aria-label={copy.preview}
                style={{
                  backgroundColor:
                    draft.theme
                      .launcherColor,
                  color:
                    draft.theme.textColor,
                }}
              >
                <MessageCircle
                  aria-hidden="true"
                />
              </button>

              {!draft.is_enabled ? (
                <div className="widget-settings-disabled-overlay">
                  <Power aria-hidden="true" />
                  <span>
                    {copy.disabledHint}
                  </span>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="widget-settings-preview-empty">
              <MessageCircle
                aria-hidden="true"
              />
              <p>{copy.chooseDescription}</p>
            </div>
          )}
        </aside>
      </div>
    </main>
  );
}
