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

  it('widget does not persist sessions in cookies or IndexedDB', () => {
    const cookieSpy = vi.spyOn(document, 'cookie', 'set');
    const indexedDbOpen = vi.fn();
    vi.stubGlobal('indexedDB', { open: indexedDbOpen });

    const widget = WidgetRoot.mount(mockConfig());
    window.WidgetAPI?.open();
    widget.remove();

    expect(cookieSpy).not.toHaveBeenCalled();
    expect(indexedDbOpen).not.toHaveBeenCalled();
    cookieSpy.mockRestore();
    vi.unstubAllGlobals();
  });
});
