import { describe, it, expect, vi } from 'vitest';
import { validateConfig } from '../../../src/config/validator.js';

const WIDGET_ID = `wgt_${'a'.repeat(20)}`;

describe('validateConfig', () => {
  it('does not silently switch incomplete live configuration to mock', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const resolved = validateConfig({});
    expect(resolved.transport).toBe('http');
    expect(resolved.widgetId).toBe('');
    expect(resolved.apiBaseUrl).toBe('');
    expect(warnSpy).toHaveBeenCalledTimes(2);
    warnSpy.mockRestore();
  });

  it('accepts and normalizes the production embed contract', () => {
    const resolved = validateConfig({
      widgetId: `  ${WIDGET_ID}  `,
      apiBaseUrl: 'https://ai.travel-x.online/some/ignored/path',
    });
    expect(resolved.widgetId).toBe(WIDGET_ID);
    expect(resolved.apiBaseUrl).toBe('https://ai.travel-x.online');
    expect(resolved.transport).toBe('http');
  });

  it('supports serverUrl only as a deprecated compatibility alias', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const resolved = validateConfig({
      widgetId: WIDGET_ID,
      serverUrl: 'https://legacy.example/path',
    });

    expect(resolved.apiBaseUrl).toBe('https://legacy.example');
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('serverUrl is deprecated'),
    );
    warnSpy.mockRestore();
  });

  it('accepts the public position option', () => {
    const resolved = validateConfig({ transport: 'mock', position: 'left' });
    expect(resolved.position).toBe('left');
    expect(resolved.positionOverride).toBe('left');
  });

  it('rejects insecure non-local HTTP and URL credentials', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    expect(
      validateConfig({ widgetId: WIDGET_ID, apiBaseUrl: 'http://example.com' })
        .apiBaseUrl,
    ).toBe('');
    expect(
      validateConfig({
        widgetId: WIDGET_ID,
        apiBaseUrl: 'https://u:p@example.com',
      }).apiBaseUrl,
    ).toBe('');
    warnSpy.mockRestore();
  });

  it('allows HTTP only for supported local development hosts', () => {
    const resolved = validateConfig({
      widgetId: WIDGET_ID,
      apiBaseUrl: 'http://127.0.0.1:8000',
    });
    expect(resolved.apiBaseUrl).toBe('http://127.0.0.1:8000');
  });

  it('requires mock mode explicitly and applies mock presentation only there', () => {
    const resolved = validateConfig({
      transport: 'mock',
      mock: {
        displayName: 'Preview agent',
        position: 'left',
        theme: { primary: '#112233' },
      },
    });
    expect(resolved.transport).toBe('mock');
    expect(resolved.displayName).toBe('Preview agent');
    expect(resolved.position).toBe('left');
    expect(resolved.theme.primary).toBe('#112233');
  });

  it('ignores unknown fields and invalid mock scenarios', () => {
    const raw = {
      transport: 'mock',
      mockScenario: 'invalid',
      unknownProp: 123,
    } as unknown as Parameters<typeof validateConfig>[0];
    const resolved = validateConfig(raw);
    expect(resolved.mockScenario).toBe('happy-path');
    expect('unknownProp' in resolved).toBe(false);
  });
});
