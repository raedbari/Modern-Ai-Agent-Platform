import type { WidgetConfig } from './config/types.js';
import { validateConfig } from './config/validator.js';
import { WidgetRoot } from './widget-root.js';

export type {
  WidgetAppearance,
  WidgetConfig,
  WidgetPosition,
} from './config/types.js';
export type { WidgetAPI } from './widget-root.js';

declare global {
  interface Window {
    WidgetConfig?: WidgetConfig;
  }
}

/** Mount one Widget instance after validating all host-controlled input. */
function bootstrap(): void {
  const config = validateConfig(readEmbedConfig());
  WidgetRoot.mount(config);
}

function readEmbedConfig(): WidgetConfig {
  if (window.WidgetConfig) return window.WidgetConfig;

  const script = findEmbedScript();
  if (!script) return {};

  let jsonConfig: WidgetConfig = {};
  const serialized = script.dataset.widgetConfig;
  if (serialized) {
    try {
      jsonConfig = JSON.parse(serialized) as WidgetConfig;
    } catch {
      console.warn(
        '[WidgetClient] Could not parse data-widget-config; using explicit data attributes.',
      );
    }
  }

  return {
    ...jsonConfig,
    widgetId: script.dataset.widgetId ?? jsonConfig.widgetId,
    apiBaseUrl: script.dataset.apiBaseUrl
      ?? script.dataset.serverUrl
      ?? jsonConfig.apiBaseUrl
      ?? jsonConfig.serverUrl,
    transport: asTransport(script.dataset.transport) ?? jsonConfig.transport,
    mockScenario: asMockScenario(script.dataset.mockScenario)
      ?? jsonConfig.mockScenario,
    language: script.dataset.language ?? jsonConfig.language,
    direction: asDirection(script.dataset.direction) ?? jsonConfig.direction,
    position: asPosition(script.dataset.position) ?? jsonConfig.position,
    launcherLabel: script.dataset.launcherLabel ?? jsonConfig.launcherLabel,
    shadowMode: asShadowMode(script.dataset.shadowMode) ?? jsonConfig.shadowMode,
  };
}

function asPosition(value: string | undefined): WidgetConfig['position'] {
  return value === 'left' || value === 'right' ? value : undefined;
}

function findEmbedScript(): HTMLScriptElement | null {
  if (document.currentScript instanceof HTMLScriptElement) {
    return document.currentScript;
  }
  const scripts = document.querySelectorAll<HTMLScriptElement>(
    'script[data-widget-id], script[data-widget-config], script[data-maap-widget]',
  );
  return scripts.item(scripts.length - 1);
}

function asTransport(value: string | undefined): WidgetConfig['transport'] {
  return value === 'http' || value === 'mock' ? value : undefined;
}

function asDirection(value: string | undefined): WidgetConfig['direction'] {
  return value === 'ltr' || value === 'rtl' || value === 'auto'
    ? value
    : undefined;
}

function asShadowMode(value: string | undefined): WidgetConfig['shadowMode'] {
  return value === 'open' || value === 'closed' ? value : undefined;
}

function asMockScenario(
  value: string | undefined,
): WidgetConfig['mockScenario'] {
  if (
    value === 'happy-path'
    || value === 'slow-response'
    || value === 'error-response'
    || value === 'stream-error-midway'
  ) {
    return value;
  }
  return undefined;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap, { once: true });
} else {
  bootstrap();
}
