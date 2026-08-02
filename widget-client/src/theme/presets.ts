import type { ThemeTokens } from '../config/types.js';

/** Light mode default token values. */
export const LIGHT_PRESET: ThemeTokens = {
  primary: '#6366f1',
  text: '#1e1e2e',
  launcherBg: '#6366f1',
  headerBg: '#6366f1',
  userBubbleBg: '#6366f1',
};

/** Dark mode default token values. */
export const DARK_PRESET: ThemeTokens = {
  primary: '#818cf8',
  text: '#e2e8f0',
  launcherBg: '#818cf8',
  headerBg: '#1e293b',
  userBubbleBg: '#4f46e5',
};

/**
 * Returns the preset most appropriate for the current OS colour scheme.
 * Defaults to LIGHT_PRESET when the media query is unavailable (e.g. jsdom).
 */
export function getPresetForMediaQuery(): ThemeTokens {
  if (
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-color-scheme: dark)').matches
  ) {
    return DARK_PRESET;
  }
  return LIGHT_PRESET;
}
