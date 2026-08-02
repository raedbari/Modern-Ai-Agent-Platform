import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WidgetRoot } from '../../src/widget-root.js';
import type { ResolvedConfig } from '../../src/config/types.js';

const CONFIG: ResolvedConfig = {
  agentId: 'integration-agent',
  theme: {},
  position: 'right',
  language: 'en',
  direction: 'auto',
  transport: 'mock',
  transportUrl: '',
  mockScenario: 'happy-path',
  launcherLabel: 'Open chat',
  welcomeMessage: 'Welcome!',
  shadowMode: 'open',
};

describe('Widget Lifecycle Integration', () => {
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

  it('full mount → open → send → receive → close → destroy cycle', async () => {
    // 1. Mount
    const widget = WidgetRoot.mount(CONFIG);
    expect(document.querySelector('maap-widget')).toBe(widget);
    expect(window.WidgetAPI).toBeDefined();

    // Flush connect timer
    const connectPromise = Promise.resolve();
    vi.advanceTimersByTime(20);
    await connectPromise;

    // 2. Open panel
    window.WidgetAPI?.open();
    const panel = widget.shadowRoot?.querySelector('.chat-panel') as HTMLElement;
    expect(panel).not.toBeNull();
    expect(panel.hidden).toBe(false);

    // 3. Send message
    const textarea = widget.shadowRoot?.querySelector('.input-bar__textarea') as HTMLTextAreaElement;
    const sendBtn = widget.shadowRoot?.querySelector('.input-bar__send') as HTMLButtonElement;

    textarea.value = 'Hello Assistant';
    textarea.dispatchEvent(new Event('input'));
    sendBtn.click();

    // Check user bubble is created
    let bubbles = widget.shadowRoot?.querySelectorAll('.message-bubble');
    expect(bubbles?.length).toBe(2); // user msg + streaming assistant msg

    // 4. Stream response to completion
    vi.advanceTimersByTime(300);
    await Promise.resolve();

    bubbles = widget.shadowRoot?.querySelectorAll('.message-bubble');
    expect(bubbles?.[1].textContent).toContain('What else can I do for you?');

    // 5. Close panel
    window.WidgetAPI?.close();
    expect(panel.hidden).toBe(true);

    // 6. Destroy
    window.WidgetAPI?.destroy();
    expect(document.querySelector('maap-widget')).toBeNull();
    expect(window.WidgetAPI).toBeUndefined();
  });
});
