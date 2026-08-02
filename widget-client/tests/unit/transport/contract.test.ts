import { describe, it, expect } from 'vitest';
import { createTransport } from '../../../src/transport/factory.js';
import type { ResolvedConfig } from '../../../src/config/types.js';

const BASE_CONFIG: ResolvedConfig = {
  agentId: 'test',
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

describe('Transport contract', () => {
  it('factory returns an object satisfying the ITransport interface', () => {
    const transport = createTransport(BASE_CONFIG);
    expect(typeof transport.connect).toBe('function');
    expect(typeof transport.send).toBe('function');
    expect(typeof transport.disconnect).toBe('function');
    expect(typeof transport.onStatusChange).toBe('function');
  });

  it('factory throws a descriptive error for websocket transport', () => {
    expect(() =>
      createTransport({ ...BASE_CONFIG, transport: 'websocket', transportUrl: 'ws://example.com' }),
    ).toThrow(/WebSocket transport is not yet implemented/);
  });

  it('factory throws a descriptive error for sse transport', () => {
    expect(() =>
      createTransport({ ...BASE_CONFIG, transport: 'sse', transportUrl: 'https://example.com/sse' }),
    ).toThrow(/SSE transport is not yet implemented/);
  });
});
