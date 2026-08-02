import type { ITransport } from './types.js';
import type { ResolvedConfig } from '../config/types.js';
import { MockTransport } from './mock/MockTransport.js';

/**
 * Factory that constructs the correct ITransport implementation based on config.
 *
 * Wave 1 supports only the "mock" transport.
 * Attempting to use "websocket" or "sse" throws a descriptive error so
 * developers get immediate, actionable feedback.
 */
export function createTransport(config: ResolvedConfig): ITransport {
  switch (config.transport) {
    case 'mock':
      return new MockTransport(config.mockScenario);

    case 'websocket':
      throw new Error(
        '[WidgetClient] WebSocket transport is not yet implemented. ' +
          'It will be available in a future wave. Use transport: "mock" for now.',
      );

    case 'sse':
      throw new Error(
        '[WidgetClient] SSE transport is not yet implemented. ' +
          'It will be available in a future wave. Use transport: "mock" for now.',
      );

    default: {
      // Exhaustive check — TypeScript will warn if a case is missed
      const _exhaustive: never = config.transport;
      throw new Error(`[WidgetClient] Unknown transport: ${String(_exhaustive)}`);
    }
  }
}
