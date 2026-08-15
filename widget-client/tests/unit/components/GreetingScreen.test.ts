import { describe, it, expect } from 'vitest';
import { GreetingScreen } from '../../../src/components/GreetingScreen.js';
import widgetStyles from '../../../src/styles/widget.css?raw';

describe('GreetingScreen', () => {
  it('renders with the provided welcome message', () => {
    const screen = new GreetingScreen('Hello there!');
    expect(screen.element.querySelector('.greeting-message')?.textContent).toBe('Hello there!');
  });

  it('has role="region" for landmark accessibility', () => {
    const screen = new GreetingScreen('Hi');
    expect(screen.element.getAttribute('role')).toBe('region');
  });

  it('setMessage() updates the visible text without creating a new element', () => {
    const screen = new GreetingScreen('Original');
    const p = screen.element.querySelector('.greeting-message');
    screen.setMessage('Updated');
    expect(p?.textContent).toBe('Updated');
  });

  it('does not use innerHTML (XSS safe)', () => {
    const payload = '<script>alert(1)</script>';
    const screen = new GreetingScreen(payload);
    // innerHTML of the container should contain escaped version
    expect(screen.element.querySelector('.greeting-message')?.innerHTML).toBe(
      '&lt;script&gt;alert(1)&lt;/script&gt;',
    );
  });

  it('is covered by the shared Shadow DOM stylesheet', () => {
    expect(widgetStyles).toContain('.greeting-screen');
  });
});
