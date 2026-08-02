import { describe, expect, it } from 'vitest';
import widgetStyles from '../../../src/styles/widget.css?raw';

describe('Widget responsive and touch styles', () => {
  it('uses the dynamic viewport and safe-area insets on mobile', () => {
    expect(widgetStyles).toContain('block-size: 100dvh');
    expect(widgetStyles).toContain('env(safe-area-inset-bottom)');
    expect(widgetStyles).toContain('env(safe-area-inset-top)');
  });

  it('keeps close and send controls at least 44px', () => {
    expect(widgetStyles).toMatch(
      /\.panel-header__close\s*\{[^}]*inline-size:\s*2\.75rem/s,
    );
    expect(widgetStyles).toMatch(
      /\.input-bar__send\s*\{[^}]*min-inline-size:\s*44px/s,
    );
  });

  it('respects reduced-motion preferences', () => {
    expect(widgetStyles).toContain('@media (prefers-reduced-motion: reduce)');
  });
});
