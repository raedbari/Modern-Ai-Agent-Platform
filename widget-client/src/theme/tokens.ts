/**
 * Mapping between ThemeTokens keys and their CSS Custom Property names.
 * All properties are scoped under the `--wc-` prefix to avoid collisions.
 */
export const TOKEN_TO_CSS_PROP: Record<string, string> = {
  primary: '--wc-primary',
  text: '--wc-text',
  launcherBg: '--wc-launcher-bg',
  headerBg: '--wc-header-bg',
  userBubbleBg: '--wc-user-bubble-bg',
} as const;

/** All supported token names in a typed array. */
export const TOKEN_KEYS = Object.keys(TOKEN_TO_CSS_PROP) as Array<keyof typeof TOKEN_TO_CSS_PROP>;
