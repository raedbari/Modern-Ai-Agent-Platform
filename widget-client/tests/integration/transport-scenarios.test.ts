import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WidgetRoot } from '../../src/widget-root.js';
import type { ResolvedConfig } from '../../src/config/types.js';

function makeConfig(scenario: ResolvedConfig['mockScenario']): ResolvedConfig {
  return {
    agentId: 'scenario-agent',
    theme: {},
    position: 'right',
    language: 'en',
    direction: 'auto',
    transport: 'mock',
    transportUrl: '',
    mockScenario: scenario,
    launcherLabel: 'Open chat',
    welcomeMessage: 'Welcome!',
    shadowMode: 'open',
  };
}

describe('Transport Scenarios Integration', () => {
  beforeEach(() => {
    document.querySelector('maap-widget')?.remove();
    delete (window as { WidgetAPI?: unknown }).WidgetAPI;
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    document.querySelector('maap-widget')?.remove();
    delete (window as { WidgetAPI?: unknown }).WidgetAPI;
  });

  it('error-response scenario transitions UI state to error bubble', async () => {
    const widget = WidgetRoot.mount(makeConfig('error-response'));
    vi.advanceTimersByTime(20);

    window.WidgetAPI?.open();
    const textarea = widget.shadowRoot?.querySelector('.input-bar__textarea') as HTMLTextAreaElement;
    const sendBtn = widget.shadowRoot?.querySelector('.input-bar__send') as HTMLButtonElement;

    textarea.value = 'Trigger Error';
    textarea.dispatchEvent(new Event('input'));
    sendBtn.click();

    await Promise.resolve();
    vi.advanceTimersByTime(50);

    const errorBubble = widget.shadowRoot?.querySelector('.message-bubble--error');
    expect(errorBubble).not.toBeNull();
  });

  it('setConfig updates theme CSS custom properties at runtime', () => {
    const widget = WidgetRoot.mount(makeConfig('happy-path'));
    window.WidgetAPI?.setConfig({ theme: { primary: '#ff0055' } });

    const fallbackStyle = widget.shadowRoot?.querySelector('#theme-injector-fallback');
    const adoptedStyle = widget.shadowRoot?.adoptedStyleSheets?.[0]?.cssRules?.[0]?.cssText;
    const cssText = fallbackStyle?.textContent || adoptedStyle || '';
    expect(cssText).toContain('--wc-primary: #ff0055');
  });
});
