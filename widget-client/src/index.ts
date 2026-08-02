import type { WidgetConfig } from './config/types.js';
import { validateConfig } from './config/validator.js';
import { WidgetRoot } from './widget-root.js';

/**
 * Widget bootstrap entry point.
 *
 * Priority order for configuration:
 *  1. `window.WidgetConfig` (set by the host page before the script loads)
 *  2. `data-widget-config` attribute on the <script> tag that loaded this bundle
 *  3. Empty config (demo / fallback mode)
 */
function bootstrap(): void {
  let raw: WidgetConfig = {};

  // 1. Check window.WidgetConfig
  if (
    typeof window !== 'undefined' &&
    Object.prototype.hasOwnProperty.call(window, 'WidgetConfig')
  ) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    raw = (window as any).WidgetConfig as WidgetConfig;
  } else {
    // 2. Check data-widget-config on the current script tag
    const currentScript =
      document.currentScript ?? document.querySelector('script[data-widget-config]');
    const attr = currentScript?.getAttribute('data-widget-config');
    if (attr) {
      try {
        raw = JSON.parse(attr) as WidgetConfig;
      } catch {
        console.warn('[WidgetClient] Could not parse data-widget-config attribute. Using defaults.');
      }
    }
  }

  const config = validateConfig(raw);
  WidgetRoot.mount(config);
}

// Auto-boot when the DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bootstrap);
} else {
  bootstrap();
}
