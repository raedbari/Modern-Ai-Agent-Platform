import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WidgetRoot } from '../../src/widget-root.js';
import { validateConfig } from '../../src/config/validator.js';
import type { ResolvedConfig } from '../../src/config/types.js';
import { mockConfig } from '../fixtures/config.js';

const DEFAULTS = mockConfig({ welcomeMessage: 'Hello!' });

function makeConfig(overrides: Partial<ResolvedConfig> = {}): ResolvedConfig {
  return { ...DEFAULTS, ...overrides };
}

describe('WidgetRoot custom element', () => {
  beforeEach(() => {
    // Clean up any existing elements
    document.querySelector('maap-widget')?.remove();
    delete (window as { WidgetAPI?: unknown }).WidgetAPI;
  });

  afterEach(() => {
    document.querySelector('maap-widget')?.remove();
    delete (window as { WidgetAPI?: unknown }).WidgetAPI;
  });

  it('registers as a custom element', () => {
    expect(customElements.get('maap-widget')).toBeDefined();
  });

  it('mounts and appends to document.body', () => {
    WidgetRoot.mount(makeConfig());
    expect(document.querySelector('maap-widget')).not.toBeNull();
  });

  it('exposes the required WidgetAPI lifecycle methods', () => {
    WidgetRoot.mount(makeConfig());
    expect(typeof window.WidgetAPI?.open).toBe('function');
    expect(typeof window.WidgetAPI?.close).toBe('function');
    expect(typeof window.WidgetAPI?.setConfig).toBe('function');
    expect(typeof window.WidgetAPI?.refresh).toBe('function');
    expect(typeof window.WidgetAPI?.destroy).toBe('function');
  });

  it('setConfig updates safe presentation settings without remounting', async () => {
    const widget = WidgetRoot.mount(makeConfig());

    await window.WidgetAPI?.setConfig({
      language: 'ar',
      direction: 'rtl',
      position: 'left',
      launcherLabel: 'افتح المحادثة',
      mock: { displayName: 'مساعد الدعم' },
    });

    expect(widget.lang).toBe('ar');
    expect(widget.dir).toBe('rtl');
    expect(widget.dataset.position).toBe('left');
    expect(
      widget.shadowRoot?.querySelector('.launcher-button')?.getAttribute(
        'aria-label',
      ),
    ).toBe('افتح المحادثة');
    expect(
      widget.shadowRoot?.querySelector('.panel-header__title')?.textContent,
    ).toBe('مساعد الدعم');
  });

  it('destroy() removes the element from DOM and deletes window.WidgetAPI', () => {
    WidgetRoot.mount(makeConfig());
    expect(document.querySelector('maap-widget')).not.toBeNull();

    window.WidgetAPI?.destroy();

    expect(document.querySelector('maap-widget')).toBeNull();
    expect(window.WidgetAPI).toBeUndefined();
  });

  it('shadow mode matches config (open)', () => {
    const el = WidgetRoot.mount(makeConfig({ shadowMode: 'open' }));
    expect(el.shadowRoot).not.toBeNull();
  });

  it('missing live identifiers triggers safe configuration warnings', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    validateConfig({});
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('data-widget-id'),
    );
    warnSpy.mockRestore();
  });

  it('defaults are applied when optional fields are missing', () => {
    const config = validateConfig({ transport: 'mock' });
    expect(config.position).toBe('right');
    expect(config.shadowMode).toBe('open');
    expect(config.transport).toBe('mock');
    expect(config.launcherLabel).toBe('Open chat');
  });

  it('mount() returns existing element instead of creating a duplicate', () => {
    WidgetRoot.mount(makeConfig());
    WidgetRoot.mount(makeConfig());
    expect(document.querySelectorAll('maap-widget')).toHaveLength(1);
  });

  it('returns focus to the launcher after the panel closes', () => {
    const widget = WidgetRoot.mount(makeConfig());
    const launcher = widget.shadowRoot?.querySelector(
      '.launcher-button',
    ) as HTMLButtonElement;

    launcher.click();
    window.WidgetAPI?.close();

    expect(widget.shadowRoot?.activeElement).toBe(launcher);
  });

  it('does not steal textarea focus while messages update', async () => {
    const widget = WidgetRoot.mount(makeConfig());
    await new Promise((resolve) => window.setTimeout(resolve, 15));
    window.WidgetAPI?.open();
    const textarea = widget.shadowRoot?.querySelector(
      '.input-bar__textarea',
    ) as HTMLTextAreaElement;
    textarea.focus();
    textarea.value = 'Keep my focus';
    textarea.dispatchEvent(new Event('input'));
    textarea.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }),
    );

    expect(widget.shadowRoot?.activeElement).toBe(textarea);
  });
});
