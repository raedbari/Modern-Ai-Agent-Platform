import type {
  ThemeTokens,
  WidgetAppearance,
} from '../config/types.js';
import { TOKEN_TO_CSS_PROP, TOKEN_KEYS } from './tokens.js';
import {
  getAppearancePreset,
  getBrandPreset,
} from './presets.js';
import { isValidCSSColor } from '../utils/color.js';

/** Apply validated API theme values inside the Widget Shadow Root. */
export class ThemeInjector {
  readonly #shadow: ShadowRoot;
  #sheet: CSSStyleSheet | null = null;

  constructor(shadow: ShadowRoot) {
    this.#shadow = shadow;
  }

  apply(
    tokens: Partial<ThemeTokens>,
    appearance: WidgetAppearance = 'light',
  ): void {
    const brandPreset = getBrandPreset(appearance);
    const resolved = { ...brandPreset };

    for (const key of TOKEN_KEYS) {
      const override = tokens[key];
      if (override !== undefined) {
        if (isValidCSSColor(override)) {
          resolved[key] = override;
        } else {
          console.warn(
            `[ThemeInjector] Invalid colour for "${key}"; using the safe preset.`,
          );
        }
      }
    }

    const appearanceTokens = getAppearancePreset(appearance);
    const declarations = [
      ...TOKEN_KEYS.map(
        (key) => `  ${TOKEN_TO_CSS_PROP[key]}: ${resolved[key]};`,
      ),
      `  --wc-surface: ${appearanceTokens.surface};`,
      `  --wc-surface-muted: ${appearanceTokens.surfaceMuted};`,
      `  --wc-body-text: ${appearanceTokens.bodyText};`,
      `  --wc-muted-text: ${appearanceTokens.mutedText};`,
      `  --wc-border: ${appearanceTokens.border};`,
      `  --wc-input-bg: ${appearanceTokens.input};`,
      `  --wc-assistant-bubble-bg: ${appearanceTokens.assistantBubble};`,
      `  --wc-error-surface: ${appearanceTokens.errorSurface};`,
      `  --wc-error-text: ${appearanceTokens.errorText};`,
    ].join('\n');

    this.#applyToSheet(`:host {\n${declarations}\n}`);
  }

  #applyToSheet(css: string): void {
    try {
      if (!this.#sheet) {
        this.#sheet = new CSSStyleSheet();
        const current = Array.isArray(this.#shadow.adoptedStyleSheets)
          ? this.#shadow.adoptedStyleSheets
          : [];
        this.#shadow.adoptedStyleSheets = [...current, this.#sheet];
      }
      this.#sheet.replaceSync(css);
    } catch {
      let fallbackStyle = this.#shadow.querySelector<HTMLStyleElement>(
        '#theme-injector-fallback',
      );
      if (!fallbackStyle) {
        fallbackStyle = document.createElement('style');
        fallbackStyle.id = 'theme-injector-fallback';
        this.#shadow.appendChild(fallbackStyle);
      }
      fallbackStyle.textContent = css;
    }
  }
}
