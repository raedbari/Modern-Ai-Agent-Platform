import type { ResolvedConfig } from './types.js';
import { LIGHT_PRESET } from '../theme/presets.js';

/** Safe fallbacks used until the trusted bootstrap response arrives. */
export const DEFAULTS: ResolvedConfig = {
  widgetId: '',
  serverUrl: '',
  transport: 'http',
  mockScenario: 'happy-path',
  language: 'en',
  direction: 'auto',
  launcherLabel: 'Open chat',
  shadowMode: 'open',
  displayName: 'Chat support',
  welcomeMessage: 'Hello! How can I help you today?',
  theme: LIGHT_PRESET,
  position: 'right',
  appearance: 'light',
};
