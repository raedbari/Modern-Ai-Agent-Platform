import type { ThemeTokens } from '../config/types.js';
import { TOKEN_TO_CSS_PROP, TOKEN_KEYS } from './tokens.js';
import { LIGHT_PRESET, getPresetForMediaQuery } from './presets.js';
import { isValidCSSColor } from '../utils/color.js';

/**
 * ThemeInjector manages CSS Custom Properties inside a Shadow Root via
 * `adoptedStyleSheets`. This approach avoids injecting <style> tags and
 * keeps tokens scoped to the widget's shadow tree.
 */
export class ThemeInjector {
  readonly #shadow: ShadowRoot;
  #sheet: CSSStyleSheet | null = null;

  constructor(shadow: ShadowRoot) {
    this.#shadow = shadow;
  }

  /**
   * Apply a set of theme tokens to the shadow root.
   *
   * Merge order:
   *  1. Media-query preset (light or dark)
   *  2. `tokens` argument overrides
   *
   * Invalid CSS colour values are rejected: the corresponding preset value
   * is used instead, and a warning is logged.
   */
  apply(tokens: Partial<ThemeTokens>): void {
    const preset = getPresetForMediaQuery();
    const resolved: Partial<ThemeTokens> = {};

    for (const key of TOKEN_KEYS) {
      const override = tokens[key as keyof ThemeTokens];
      const fallback = preset[key as keyof ThemeTokens] ?? LIGHT_PRESET[key as keyof ThemeTokens];

      if (override !== undefined) {
        if (isValidCSSColor(override)) {
          resolved[key as keyof ThemeTokens] = override;
        } else {
          console.warn(
            `[ThemeInjector] "${override}" is not a valid CSS colour for token "${key}". Using preset value "${fallback}".`,
          );
          resolved[key as keyof ThemeTokens] = fallback;
        }
      } else {
        resolved[key as keyof ThemeTokens] = fallback;
      }
    }

    this.#applyToSheet(resolved as ThemeTokens);
  }

  // ─── Private helpers ──────────────────────────────────────────────────────

  #applyToSheet(tokens: ThemeTokens): void {
    const declarations = TOKEN_KEYS.map((key) => {
      const prop = TOKEN_TO_CSS_PROP[key];
      const value = tokens[key as keyof ThemeTokens];
      return `  ${prop}: ${value};`;
    }).join('\n');

    const css = `:host {\n${declarations}\n}`;

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
      // Fallback for environments without native adoptedStyleSheets support (e.g. basic jsdom)
      let fallbackStyle = this.#shadow.querySelector<HTMLStyleElement>('#theme-injector-fallback');
      if (!fallbackStyle) {
        fallbackStyle = document.createElement('style');
        fallbackStyle.id = 'theme-injector-fallback';
        this.#shadow.appendChild(fallbackStyle);
      }
      fallbackStyle.textContent = css;
    }
  }
}
