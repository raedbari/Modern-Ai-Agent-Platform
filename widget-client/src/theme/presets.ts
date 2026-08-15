import type {
  ThemeTokens,
  WidgetAppearance,
} from '../config/types.js';

/** Safe brand fallbacks shown before a live bootstrap completes. */
export const LIGHT_PRESET: ThemeTokens = {
  primary: '#2563EB',
  onPrimary: '#FFFFFF',
  launcherBg: '#2563EB',
  headerBg: '#2563EB',
  userBubbleBg: '#2563EB',
};

export const DARK_PRESET: ThemeTokens = {
  primary: '#60A5FA',
  onPrimary: '#FFFFFF',
  launcherBg: '#2563EB',
  headerBg: '#1D4ED8',
  userBubbleBg: '#2563EB',
};

export interface AppearanceTokens {
  surface: string;
  surfaceMuted: string;
  bodyText: string;
  mutedText: string;
  border: string;
  input: string;
  assistantBubble: string;
  errorSurface: string;
  errorText: string;
}

const LIGHT_APPEARANCE: AppearanceTokens = {
  surface: '#FFFFFF',
  surfaceMuted: '#F8FAFC',
  bodyText: '#0F172A',
  mutedText: '#64748B',
  border: '#E2E8F0',
  input: '#FFFFFF',
  assistantBubble: '#F1F5F9',
  errorSurface: '#FEE2E2',
  errorText: '#B91C1C',
};

const DARK_APPEARANCE: AppearanceTokens = {
  surface: '#111827',
  surfaceMuted: '#0F172A',
  bodyText: '#F8FAFC',
  mutedText: '#CBD5E1',
  border: '#334155',
  input: '#1E293B',
  assistantBubble: '#1E293B',
  errorSurface: '#450A0A',
  errorText: '#FCA5A5',
};

export function getBrandPreset(appearance: WidgetAppearance): ThemeTokens {
  return appearance === 'dark' ? DARK_PRESET : LIGHT_PRESET;
}

export function getAppearancePreset(
  appearance: WidgetAppearance,
): AppearanceTokens {
  return appearance === 'dark' ? DARK_APPEARANCE : LIGHT_APPEARANCE;
}
