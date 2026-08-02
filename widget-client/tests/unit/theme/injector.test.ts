import { describe, it, expect, beforeEach, vi } from 'vitest';
import { TOKEN_KEYS } from '../../../src/theme/tokens.js';
import { LIGHT_PRESET, DARK_PRESET } from '../../../src/theme/presets.js';

/**
 * jsdom does not fully support adoptedStyleSheets or CSSStyleSheet.replaceSync.
 * We polyfill the minimum required surface for these tests.
 */
function setupCSSPolyfills(): void {
  // Polyfill CSSStyleSheet with replaceSync if not available
  if (typeof CSSStyleSheet === 'undefined' || !CSSStyleSheet.prototype.replaceSync) {
    const MockCSSStyleSheet = class {
      cssRules: Array<{ cssText: string }> = [];
      replaceSync(css: string): void {
        this.cssRules = [{ cssText: css }];
      }
    };
    (globalThis as Record<string, unknown>).CSSStyleSheet = MockCSSStyleSheet;
  }

  // Polyfill CSS.supports to make it strict about colours
  (globalThis as Record<string, unknown>).CSS = {
    supports: (_prop: string, _value: string): boolean => {
      // In tests, we rely on a strict implementation:
      // valid CSS colours match a simplified regex
      if (_prop === 'color') {
        if (_value === 'not-a-colour' || _value === 'invalid') return false;
        return /^(#[0-9a-fA-F]{3,8}|rgb|rgba|hsl|hsla|transparent|currentColor|inherit|initial|unset)/.test(
          _value.trim(),
        );
      }
      return true;
    },
  };
}

/** Create a ShadowRoot with polyfilled adoptedStyleSheets. */
function makeMockShadow(): ShadowRoot {
  const el = document.createElement('div');
  document.body.appendChild(el);
  const shadow = el.attachShadow({ mode: 'open' });

  let sheets: CSSStyleSheet[] = [];
  Object.defineProperty(shadow, 'adoptedStyleSheets', {
    get: () => sheets,
    set: (v: CSSStyleSheet[]) => { sheets = v; },
    configurable: true,
  });

  return shadow;
}

describe('Theme presets', () => {
  it('light preset contains all required tokens', () => {
    for (const key of TOKEN_KEYS) {
      expect(LIGHT_PRESET[key as keyof typeof LIGHT_PRESET]).toBeTruthy();
    }
  });

  it('dark preset contains all required tokens', () => {
    for (const key of TOKEN_KEYS) {
      expect(DARK_PRESET[key as keyof typeof DARK_PRESET]).toBeTruthy();
    }
  });
});

describe('ThemeInjector', () => {
  let shadow: ShadowRoot;

  beforeEach(async () => {
    setupCSSPolyfills();
    shadow = makeMockShadow();
  });

  async function makeInjector() {
    // Import after polyfills are set up so the module picks up the mocked CSS global
    const { ThemeInjector } = await import('../../../src/theme/injector.js');
    return new ThemeInjector(shadow);
  }

  it('apply() adds an adoptedStyleSheet to the shadow root', async () => {
    const injector = await makeInjector();
    injector.apply({});
    expect(shadow.adoptedStyleSheets).toHaveLength(1);
  });

  it('apply() sets :host custom properties', async () => {
    const injector = await makeInjector();
    injector.apply({ primary: '#ff0000' });
    const cssText = shadow.adoptedStyleSheets[0]?.cssRules[0]?.cssText ?? '';
    expect(cssText).toContain('--wc-primary');
    expect(cssText).toContain('#ff0000');
  });

  it('apply() called twice is idempotent (still one sheet)', async () => {
    const injector = await makeInjector();
    injector.apply({});
    injector.apply({});
    expect(shadow.adoptedStyleSheets).toHaveLength(1);
  });

  it('invalid colour falls back to preset value and logs a warning', async () => {
    const injector = await makeInjector();
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    // 'not-a-colour' won't match our CSS.supports regex
    injector.apply({ primary: 'not-a-colour' });
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('Invalid colour'));
    warnSpy.mockRestore();

    // Should still produce a valid stylesheet using the preset colour
    const cssText = shadow.adoptedStyleSheets[0]?.cssRules[0]?.cssText ?? '';
    expect(cssText).toContain('--wc-primary');
    expect(cssText).toContain(LIGHT_PRESET.primary);
  });

  it('explicit token overrides the preset', async () => {
    const injector = await makeInjector();
    injector.apply({ primary: '#abcdef' });
    const cssText = shadow.adoptedStyleSheets[0]?.cssRules[0]?.cssText ?? '';
    // Verify the primary property specifically uses the override
    expect(cssText).toContain('--wc-primary: #abcdef');
    // Verify primary is NOT using the preset value
    expect(cssText).not.toContain('--wc-primary: ' + LIGHT_PRESET.primary);
  });

  it('dark appearance explicitly activates the dark preset', async () => {
    const darkShadow = makeMockShadow();
    const { ThemeInjector } = await import('../../../src/theme/injector.js');
    const darkInjector = new ThemeInjector(darkShadow);
    darkInjector.apply({}, 'dark');

    const cssText = darkShadow.adoptedStyleSheets[0]?.cssRules[0]?.cssText ?? '';
    expect(cssText).toContain(DARK_PRESET.primary);
  });
});
