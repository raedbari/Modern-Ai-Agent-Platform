import type { WidgetConfig, ResolvedConfig } from './types.js';
import { DEFAULTS } from './defaults.js';

const VALID_POSITIONS = new Set<string>(['left', 'right']);
const VALID_TRANSPORTS = new Set<string>(['mock', 'websocket', 'sse']);
const VALID_MOCK_SCENARIOS = new Set<string>([
  'happy-path',
  'slow-response',
  'error-response',
  'stream-error-midway',
]);
const VALID_SHADOW_MODES = new Set<string>(['open', 'closed']);
const VALID_DIRECTIONS = new Set<string>(['ltr', 'rtl', 'auto']);

/**
 * Validates and resolves raw WidgetConfig into ResolvedConfig.
 *
 * - Warns (but does not throw) on missing agentId.
 * - Falls back to "mock" transport when transportUrl is invalid for websocket/sse.
 * - Unknown or unrecognised fields are silently ignored.
 */
export function validateConfig(raw: WidgetConfig): ResolvedConfig {
  if (!raw.agentId) {
    console.warn(
      '[WidgetClient] agentId is not set. The widget will run in demo mode.',
    );
  }

  // Resolve transport — fall back to mock if real transport lacks a valid URL
  let transport = VALID_TRANSPORTS.has(raw.transport ?? '')
    ? (raw.transport as ResolvedConfig['transport'])
    : DEFAULTS.transport;

  let transportUrl = DEFAULTS.transportUrl;
  if (transport === 'websocket' || transport === 'sse') {
    if (raw.transportUrl && isValidUrl(raw.transportUrl)) {
      transportUrl = raw.transportUrl;
    } else {
      console.warn(
        `[WidgetClient] Invalid or missing transportUrl for transport "${transport}". Falling back to mock.`,
      );
      transport = 'mock';
    }
  }

  const position = VALID_POSITIONS.has(raw.position ?? '')
    ? (raw.position as ResolvedConfig['position'])
    : DEFAULTS.position;

  const direction = VALID_DIRECTIONS.has(raw.direction ?? '')
    ? (raw.direction as ResolvedConfig['direction'])
    : DEFAULTS.direction;

  const mockScenario = VALID_MOCK_SCENARIOS.has(raw.mockScenario ?? '')
    ? (raw.mockScenario as ResolvedConfig['mockScenario'])
    : DEFAULTS.mockScenario;

  const shadowMode = VALID_SHADOW_MODES.has(raw.shadowMode ?? '')
    ? (raw.shadowMode as ResolvedConfig['shadowMode'])
    : DEFAULTS.shadowMode;

  return {
    agentId: raw.agentId ?? '',
    theme: raw.theme ?? {},
    position,
    language: raw.language ?? DEFAULTS.language,
    direction,
    transport,
    transportUrl,
    mockScenario,
    launcherLabel: raw.launcherLabel ?? DEFAULTS.launcherLabel,
    welcomeMessage: raw.welcomeMessage ?? DEFAULTS.welcomeMessage,
    shadowMode,
  };
}

function isValidUrl(value: string): boolean {
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
}
