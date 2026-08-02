import type { ITransport } from './types.js';
import type { ResolvedConfig } from '../config/types.js';
import { HttpTransport } from './http/HttpTransport.js';
import { MockTransport } from './mock/MockTransport.js';

/** Construct the explicit local mock or the production HTTP transport. */
export function createTransport(config: ResolvedConfig): ITransport {
  if (config.transport === 'mock') {
    return new MockTransport(config.mockScenario);
  }
  return new HttpTransport({
    serverUrl: config.serverUrl,
    widgetId: config.widgetId,
  });
}
