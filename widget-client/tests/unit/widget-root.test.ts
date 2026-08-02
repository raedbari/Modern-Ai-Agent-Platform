import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WidgetRoot } from '../../src/widget-root.js';
import { validateConfig } from '../../src/config/validator.js';
import type { ResolvedConfig } from '../../src/config/types.js';

const DEFAULTS: ResolvedConfig = {
  agentId: 'test-agent',
  theme: {},
  position: 'right',
  language: 'en',
  direction: 'auto',
  transport: 'mock',
  transportUrl: '',
  mockScenario: 'happy-path',
  launcherLabel: 'Open chat',
  welcomeMessage: 'Hello!',
  shadowMode: 'open',
};

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

  it('exposes window.WidgetAPI with all 4 methods', () => {
    WidgetRoot.mount(makeConfig());
    expect(typeof window.WidgetAPI?.open).toBe('function');
    expect(typeof window.WidgetAPI?.close).toBe('function');
    expect(typeof window.WidgetAPI?.destroy).toBe('function');
    expect(typeof window.WidgetAPI?.setConfig).toBe('function');
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

  it('missing agentId triggers console.warn', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    validateConfig({});
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('agentId is not set'),
    );
    warnSpy.mockRestore();
  });

  it('defaults are applied when optional fields are missing', () => {
    const config = validateConfig({ agentId: 'x' });
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
});
