import type {
  MockScenario,
  ResolvedConfig,
  ThemeTokens,
  WidgetAppearance,
  WidgetConfig,
  WidgetPosition,
} from './types.js';
import { DEFAULTS } from './defaults.js';
import { isValidCSSColor } from '../utils/color.js';

const PUBLIC_WIDGET_ID = /^wgt_[A-Za-z0-9_-]{20,60}$/;
const VALID_MOCK_SCENARIOS = new Set<MockScenario>([
  'happy-path',
  'slow-response',
  'error-response',
  'stream-error-midway',
]);
const VALID_SHADOW_MODES = new Set(['open', 'closed']);
const VALID_DIRECTIONS = new Set(['ltr', 'rtl', 'auto']);
const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);

/** Validate untrusted embed configuration without silently enabling demo mode. */
export function validateConfig(raw: WidgetConfig): ResolvedConfig {
  const transport = raw.transport === 'mock' ? 'mock' : 'http';
  const widgetId = normalizeWidgetId(raw.widgetId);
  const legacyServerUrl = raw.serverUrl?.trim();
  if (legacyServerUrl && !raw.apiBaseUrl) {
    console.warn(
      '[WidgetClient] serverUrl is deprecated; use apiBaseUrl instead.',
    );
  }
  const apiBaseUrl = normalizeApiBaseUrl(raw.apiBaseUrl ?? legacyServerUrl);

  if (transport === 'http' && !widgetId) {
    console.warn(
      '[WidgetClient] A valid data-widget-id is required for live chat.',
    );
  }
  if (transport === 'http' && !apiBaseUrl) {
    console.warn(
      '[WidgetClient] A valid HTTPS apiBaseUrl is required for live chat.',
    );
  }

  const mockScenario = VALID_MOCK_SCENARIOS.has(
    raw.mockScenario as MockScenario,
  )
    ? (raw.mockScenario as MockScenario)
    : DEFAULTS.mockScenario;

  const direction = VALID_DIRECTIONS.has(raw.direction ?? '')
    ? (raw.direction as ResolvedConfig['direction'])
    : DEFAULTS.direction;

  const shadowMode = VALID_SHADOW_MODES.has(raw.shadowMode ?? '')
    ? (raw.shadowMode as ResolvedConfig['shadowMode'])
    : DEFAULTS.shadowMode;

  const mock = transport === 'mock' ? raw.mock : undefined;

  const positionOverride = resolveOptionalPosition(raw.position);

  return {
    ...DEFAULTS,
    widgetId,
    apiBaseUrl,
    transport,
    mockScenario,
    language: normalizeShortText(raw.language, DEFAULTS.language, 35),
    direction,
    launcherLabel: normalizeShortText(
      raw.launcherLabel,
      DEFAULTS.launcherLabel,
      100,
    ),
    shadowMode,
    displayName: normalizeShortText(
      mock?.displayName,
      DEFAULTS.displayName,
      255,
    ),
    welcomeMessage: normalizeShortText(
      mock?.welcomeMessage,
      DEFAULTS.welcomeMessage,
      500,
    ),
    theme: resolveMockTheme(mock?.theme),
    position: positionOverride ?? resolvePosition(mock?.position),
    positionOverride,
    appearance: resolveAppearance(mock?.appearance),
  };
}

function normalizeWidgetId(value: string | undefined): string {
  const normalized = value?.trim() ?? '';
  return PUBLIC_WIDGET_ID.test(normalized) ? normalized : '';
}

function normalizeApiBaseUrl(value: string | undefined): string {
  if (!value) return '';
  try {
    const url = new URL(value);
    const localHttp = url.protocol === 'http:' && LOCAL_HOSTS.has(url.hostname);
    if (
      (url.protocol !== 'https:' && !localHttp)
      || url.username
      || url.password
    ) {
      return '';
    }
    return url.origin;
  } catch {
    return '';
  }
}

function resolveOptionalPosition(
  value: WidgetPosition | undefined,
): WidgetPosition | undefined {
  return value === 'left' || value === 'right' ? value : undefined;
}

function normalizeShortText(
  value: string | undefined,
  fallback: string,
  maxLength: number,
): string {
  const normalized = value?.trim();
  if (!normalized || normalized.length > maxLength) return fallback;
  return normalized;
}

function resolvePosition(value: WidgetPosition | undefined): WidgetPosition {
  return value === 'left' || value === 'right' ? value : DEFAULTS.position;
}

function resolveAppearance(
  value: WidgetAppearance | undefined,
): WidgetAppearance {
  return value === 'dark' || value === 'light'
    ? value
    : DEFAULTS.appearance;
}

function resolveMockTheme(value: Partial<ThemeTokens> | undefined): ThemeTokens {
  const resolved = { ...DEFAULTS.theme };
  if (!value) return resolved;
  for (const key of Object.keys(resolved) as Array<keyof ThemeTokens>) {
    const candidate = value[key];
    if (candidate && isValidCSSColor(candidate)) {
      resolved[key] = candidate;
    }
  }
  return resolved;
}
