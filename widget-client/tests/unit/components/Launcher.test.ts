import { describe, it, expect, vi } from 'vitest';
import { Launcher } from '../../../src/components/Launcher.js';

describe('Launcher component', () => {
  it('has part="launcher-button" attribute', () => {
    const launcher = new Launcher({ onClick: vi.fn() });
    expect(launcher.element.getAttribute('part')).toBe('launcher-button');
  });

  it('aria-label defaults to provided label or fallback', () => {
    const launcher = new Launcher({ onClick: vi.fn() }, 'Chat with AI');
    expect(launcher.element.getAttribute('aria-label')).toBe('Chat with AI');
  });

  it('aria-expanded tracks panel state', () => {
    const launcher = new Launcher({ onClick: vi.fn() });
    expect(launcher.element.getAttribute('aria-expanded')).toBe('false');

    launcher.setExpanded(true);
    expect(launcher.element.getAttribute('aria-expanded')).toBe('true');

    launcher.setExpanded(false);
    expect(launcher.element.getAttribute('aria-expanded')).toBe('false');
  });

  it('renders deterministic chat and close SVG icons', () => {
    const launcher = new Launcher({ onClick: vi.fn() });
    const closePaths = launcher.element.querySelectorAll(
      '.launcher-icon--close path',
    );

    expect(launcher.element.querySelectorAll('svg')).toHaveLength(2);
    expect(launcher.element.querySelector('.launcher-icon--chat')).not.toBeNull();
    expect(launcher.element.querySelector('.launcher-icon--close')).not.toBeNull();
    expect(Array.from(closePaths, (path) => path.getAttribute('d'))).toEqual([
      'M18 6 6 18',
      'M6 6 18 18',
    ]);
  });

  it('reflects connection state without changing its accessible label', () => {
    const launcher = new Launcher({ onClick: vi.fn() }, 'Open support');

    launcher.setConnectionStatus('connected');

    expect(launcher.element.dataset.status).toBe('connected');
    expect(launcher.element.getAttribute('aria-label')).toBe('Open support');
  });

  it('clicking button invokes onClick callback', () => {
    const onClick = vi.fn();
    const launcher = new Launcher({ onClick });
    launcher.element.click();
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('setLabel updates aria-label', () => {
    const launcher = new Launcher({ onClick: vi.fn() });
    launcher.setLabel('New Label');
    expect(launcher.element.getAttribute('aria-label')).toBe('New Label');
  });

  it('CSS styles guarantee minimum 44px touch target', () => {
    const styles = Launcher.styles();
    expect(styles).toContain('min-inline-size: 44px');
    expect(styles).toContain('min-block-size: 44px');
  });

  it('CSS defines a mirrored speech-bubble tail for left placement', () => {
    const styles = Launcher.styles();

    expect(styles).toContain('border-end-end-radius: 0.45rem');
    expect(styles).toContain(":host([data-position='left']) .launcher-button");
    expect(styles).toContain('border-end-start-radius: 0.45rem');
  });
});
