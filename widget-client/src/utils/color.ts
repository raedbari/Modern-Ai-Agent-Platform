/**
 * Returns true when `value` is a valid CSS colour according to the browser.
 * Uses CSS.supports which is available in all target browsers.
 *
 * Falls back to a basic non-empty string check in environments where
 * CSS.supports is unavailable (e.g. SSR, older jsdom).
 */
export function isValidCSSColor(value: string): boolean {
  if (typeof CSS !== 'undefined' && typeof CSS.supports === 'function') {
    return CSS.supports('color', value);
  }
  // Graceful degradation: treat any non-empty string as potentially valid
  return value.trim().length > 0;
}
