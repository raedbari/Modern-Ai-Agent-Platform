import { DEFAULTS } from '../../src/config/defaults.js';
import type { ResolvedConfig } from '../../src/config/types.js';

/** Build a complete, explicit mock configuration for DOM-level tests. */
export function mockConfig(
  overrides: Partial<ResolvedConfig> = {},
): ResolvedConfig {
  return {
    ...DEFAULTS,
    transport: 'mock',
    displayName: 'Test assistant',
    welcomeMessage: 'Welcome!',
    ...overrides,
    theme: {
      ...DEFAULTS.theme,
      ...overrides.theme,
    },
  };
}
