import { describe, it, expect } from 'vitest';
import { createTransport } from '../../../src/transport/factory.js';
import { HttpTransport } from '../../../src/transport/http/HttpTransport.js';
import { MockTransport } from '../../../src/transport/mock/MockTransport.js';
import { mockConfig } from '../../fixtures/config.js';

describe('Transport contract', () => {
  it('creates the explicit local mock transport', () => {
    expect(createTransport(mockConfig())).toBeInstanceOf(MockTransport);
  });

  it('creates HTTP transport for the production contract', () => {
    const config = mockConfig({
      transport: 'http',
      widgetId: `wgt_${'a'.repeat(20)}`,
      apiBaseUrl: 'https://ai.travel-x.online',
    });
    const transport = createTransport(config);
    expect(transport).toBeInstanceOf(HttpTransport);
    expect(typeof transport.connect).toBe('function');
    expect(typeof transport.send).toBe('function');
    expect(typeof transport.disconnect).toBe('function');
    expect(typeof transport.onStatusChange).toBe('function');
  });
});
