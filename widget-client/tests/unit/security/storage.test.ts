import { describe, it, expect, vi } from 'vitest';
import { WidgetRoot } from '../../../src/widget-root.js';

describe('Security Verification: Storage Isolation', () => {
  it('widget never writes to localStorage or sessionStorage during lifecycle', () => {
    const setLocalSpy = vi.spyOn(Storage.prototype, 'setItem');

    const widget = WidgetRoot.mount({
      agentId: 'sec-agent',
      theme: {},
      position: 'right',
      language: 'en',
      direction: 'auto',
      transport: 'mock',
      transportUrl: '',
      mockScenario: 'happy-path',
      launcherLabel: 'Chat',
      welcomeMessage: 'Hi',
      shadowMode: 'open',
    });

    window.WidgetAPI?.open();
    window.WidgetAPI?.close();
    widget.remove();

    expect(setLocalSpy).not.toHaveBeenCalled();
    setLocalSpy.mockRestore();
  });
});
