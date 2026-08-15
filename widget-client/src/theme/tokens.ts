import type { ThemeTokens } from '../config/types.js';

/** Brand token to scoped CSS custom-property mapping. */
export const TOKEN_TO_CSS_PROP: Record<keyof ThemeTokens, string> = {
  primary: '--wc-primary',
  onPrimary: '--wc-on-primary',
  launcherBg: '--wc-launcher-bg',
  headerBg: '--wc-header-bg',
  userBubbleBg: '--wc-user-bubble-bg',
};

export const TOKEN_KEYS = Object.keys(TOKEN_TO_CSS_PROP) as Array<
  keyof ThemeTokens
>;
