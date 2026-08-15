export type WidgetAppearance =
  | "light"
  | "dark";

export type WidgetPosition =
  | "left"
  | "right";

export type WidgetTheme = {
  primaryColor: string;
  textColor: string;
  launcherColor: string;
  headerColor: string;
  userMessageColor: string;
  position: WidgetPosition;
  appearance: WidgetAppearance;
};

export type WidgetSettingsRecord = {
  tenant_id: string;
  agent_id: string;
  public_widget_id: string;
  is_enabled: boolean;
  display_name: string | null;
  greeting: string | null;
  theme: WidgetTheme;
  allowed_origins: string[];
};

export type WidgetSettingsPutPayload = {
  is_enabled: boolean;
  display_name: string | null;
  greeting: string | null;
  theme: WidgetTheme;
  allowed_origins: string[];
};

export const defaultWidgetTheme: WidgetTheme = {
  primaryColor: "#2563EB",
  textColor: "#FFFFFF",
  launcherColor: "#2563EB",
  headerColor: "#2563EB",
  userMessageColor: "#2563EB",
  position: "right",
  appearance: "light",
};

export function createDefaultWidgetPayload(
  agentName: string,
): WidgetSettingsPutPayload {
  return {
    is_enabled: false,
    display_name: agentName,
    greeting: null,
    theme: {
      ...defaultWidgetTheme,
    },
    allowed_origins: [],
  };
}
