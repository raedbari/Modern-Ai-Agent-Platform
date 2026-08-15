import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { FocusTrap } from '../../../src/a11y/focus-trap.js';

describe('FocusTrap', () => {
  let container: HTMLElement;
  let trap: FocusTrap;

  beforeEach(() => {
    container = document.createElement('div');
    container.innerHTML = `
      <button id="b1">First</button>
      <input id="i1" type="text" />
      <button id="b2">Last</button>
    `;
    document.body.appendChild(container);
    trap = new FocusTrap();
  });

  afterEach(() => {
    trap.deactivate();
    container.remove();
  });

  it('focuses first focusable element on activate()', () => {
    trap.activate(container);
    expect(document.activeElement?.id).toBe('b1');
  });

  it('restores focus to trigger element on deactivate()', () => {
    const trigger = document.createElement('button');
    trigger.id = 'trigger';
    document.body.appendChild(trigger);
    trigger.focus();

    trap.activate(container);
    expect(document.activeElement?.id).toBe('b1');

    trap.deactivate();
    expect(document.activeElement?.id).toBe('trigger');
    trigger.remove();
  });

  it('Escape key triggers onEscape callback', () => {
    const onEscape = vi.fn();
    trap.activate(container, onEscape);

    const event = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
    document.dispatchEvent(event);

    expect(onEscape).toHaveBeenCalledTimes(1);
  });

  it('Tab on last element wraps to first', () => {
    trap.activate(container);
    const lastBtn = container.querySelector('#b2') as HTMLElement;
    lastBtn.focus();

    const event = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true });
    document.dispatchEvent(event);

    expect(document.activeElement?.id).toBe('b1');
  });

  it('Shift+Tab on first element wraps to last', () => {
    trap.activate(container);
    const firstBtn = container.querySelector('#b1') as HTMLElement;
    firstBtn.focus();

    const event = new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true });
    document.dispatchEvent(event);

    expect(document.activeElement?.id).toBe('b2');
  });

  it('reads the active element from the containing ShadowRoot', () => {
    const host = document.createElement('div');
    const shadow = host.attachShadow({ mode: 'open' });
    const shadowContainer = document.createElement('div');
    shadowContainer.innerHTML = `
      <button id="shadow-first">First</button>
      <button id="shadow-last">Last</button>
    `;
    shadow.appendChild(shadowContainer);
    document.body.appendChild(host);

    trap.activate(shadowContainer);
    const first = shadowContainer.querySelector('#shadow-first') as HTMLElement;
    const last = shadowContainer.querySelector('#shadow-last') as HTMLElement;
    last.focus();

    document.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'Tab',
      bubbles: true,
    }));

    expect(shadow.activeElement).toBe(first);
    trap.deactivate();
    host.remove();
  });
});
