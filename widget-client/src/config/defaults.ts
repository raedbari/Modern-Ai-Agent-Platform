import type { ResolvedConfig } from './types.js';

/** Default values applied for every optional WidgetConfig field. */
export const DEFAULTS: Omit<ResolvedConfig, 'agentId' | 'theme'> = {
  position: 'right',
  language: 'en',
  direction: 'auto',
  transport: 'mock',
  transportUrl: '',
  mockScenario: 'happy-path',
  launcherLabel: 'Open chat',
  welcomeMessage: 'Hello! How can I help you today?',
  shadowMode: 'open',
};
