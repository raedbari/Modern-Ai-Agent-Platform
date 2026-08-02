import { describe, it, expect, vi } from 'vitest';
import { validateConfig } from '../../../src/config/validator.js';

describe('validateConfig', () => {
  it('warns on missing agentId', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    validateConfig({});
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('agentId is not set'));
    warnSpy.mockRestore();
  });

  it('ignores unknown or extra fields', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const raw: any = { agentId: 'a1', unknownProp: 123, fooBar: 'baz' };
    const resolved = validateConfig(raw);
    expect(resolved.agentId).toBe('a1');
    expect('unknownProp' in resolved).toBe(false);
  });

  it('falls back to mock transport when transportUrl is invalid for websocket', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const resolved = validateConfig({
      agentId: 'a1',
      transport: 'websocket',
      transportUrl: 'invalid-url',
    });
    expect(resolved.transport).toBe('mock');
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('Invalid or missing transportUrl'));
    warnSpy.mockRestore();
  });

  it('accepts valid transportUrl for websocket', () => {
    const resolved = validateConfig({
      agentId: 'a1',
      transport: 'websocket',
      transportUrl: 'ws://localhost:8000/ws',
    });
    expect(resolved.transport).toBe('websocket');
    expect(resolved.transportUrl).toBe('ws://localhost:8000/ws');
  });

  it('falls back to default position if invalid position provided', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const resolved = validateConfig({ agentId: 'a1', position: 'top' as any });
    expect(resolved.position).toBe('right');
  });

  it('falls back to default mockScenario if invalid scenario provided', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const resolved = validateConfig({ agentId: 'a1', mockScenario: 'invalid' as any });
    expect(resolved.mockScenario).toBe('happy-path');
  });
});
