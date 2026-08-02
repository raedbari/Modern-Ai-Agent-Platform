import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { DirectionController } from '../../../src/utils/direction.js';

describe('DirectionController', () => {
  beforeEach(() => {
    document.documentElement.removeAttribute('dir');
  });

  afterEach(() => {
    document.documentElement.removeAttribute('dir');
  });

  it('defaults to ltr when dir attribute is absent', () => {
    const onChange = vi.fn();
    const ctrl = new DirectionController({ onChange });
    expect(ctrl.direction).toBe('ltr');
    ctrl.disconnect();
  });

  it('detects rtl dir on documentElement', () => {
    document.documentElement.setAttribute('dir', 'rtl');
    const onChange = vi.fn();
    const ctrl = new DirectionController({ onChange });
    expect(ctrl.direction).toBe('rtl');
    ctrl.disconnect();
  });

  it('respects explicit ltr mode override regardless of document dir', () => {
    document.documentElement.setAttribute('dir', 'rtl');
    const onChange = vi.fn();
    const ctrl = new DirectionController({ mode: 'ltr', onChange });
    expect(ctrl.direction).toBe('ltr');
    ctrl.disconnect();
  });

  it('observes runtime changes via MutationObserver', async () => {
    const onChange = vi.fn();
    const ctrl = new DirectionController({ mode: 'auto', onChange });

    document.documentElement.setAttribute('dir', 'rtl');

    // Wait for MutationObserver callback
    await new Promise((r) => setTimeout(r, 20));

    expect(onChange).toHaveBeenCalledWith('rtl');
    expect(ctrl.direction).toBe('rtl');
    ctrl.disconnect();
  });

  it('disconnect stops mutation observation', async () => {
    const onChange = vi.fn();
    const ctrl = new DirectionController({ mode: 'auto', onChange });
    ctrl.disconnect();

    document.documentElement.setAttribute('dir', 'rtl');
    await new Promise((r) => setTimeout(r, 20));

    expect(onChange).not.toHaveBeenCalled();
  });
});
