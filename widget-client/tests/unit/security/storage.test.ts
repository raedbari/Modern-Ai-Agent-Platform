import { describe, it, expect, vi } from 'vitest';
import { WidgetRoot } from '../../../src/widget-root.js';
import { mockConfig } from '../../fixtures/config.js';

describe('Security Verification: Storage Isolation', () => {
  it('widget never writes to localStorage or sessionStorage during lifecycle', () => {
    const setLocalSpy = vi.spyOn(Storage.prototype, 'setItem');

    const widget = WidgetRoot.mount(mockConfig({
      launcherLabel: 'Chat',
      welcomeMessage: 'Hi',
    }));

    window.WidgetAPI?.open();
    window.WidgetAPI?.close();
    widget.remove();

    expect(setLocalSpy).not.toHaveBeenCalled();
    setLocalSpy.mockRestore();
  });
});
