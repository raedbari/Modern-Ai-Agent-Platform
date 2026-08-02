import { describe, it, expect, vi } from 'vitest';
import { InputBar } from '../../../src/components/InputBar.js';

function makeInputBar(onSend = vi.fn()) {
  return new InputBar({ onSend });
}

function getTextarea(bar: InputBar): HTMLTextAreaElement {
  return bar.element.querySelector('.input-bar__textarea') as HTMLTextAreaElement;
}

function getSendBtn(bar: InputBar): HTMLButtonElement {
  return bar.element.querySelector('.input-bar__send') as HTMLButtonElement;
}

function getCounter(bar: InputBar): HTMLElement {
  return bar.element.querySelector('.input-bar__counter') as HTMLElement;
}

describe('InputBar', () => {
  it('has part="input-bar" attribute', () => {
    const bar = makeInputBar();
    expect(bar.element.getAttribute('part')).toBe('input-bar');
  });

  it('textarea is not disabled (inputEditable is always true)', () => {
    const bar = makeInputBar();
    expect(getTextarea(bar).disabled).toBe(false);
  });

  it('send button is disabled when textarea is empty', () => {
    const bar = makeInputBar();
    expect(getSendBtn(bar).disabled).toBe(true);
  });

  it('send button is enabled when textarea has text', () => {
    const bar = makeInputBar();
    const ta = getTextarea(bar);
    ta.value = 'Hello';
    ta.dispatchEvent(new Event('input'));
    expect(getSendBtn(bar).disabled).toBe(false);
  });

  it('send button remains disabled when sendDisabled=true even with text', () => {
    const bar = makeInputBar();
    bar.setSendDisabled(true);
    const ta = getTextarea(bar);
    ta.value = 'Hello';
    ta.dispatchEvent(new Event('input'));
    expect(getSendBtn(bar).disabled).toBe(true);
  });

  it('clicking send calls onSend with trimmed text and clears textarea', () => {
    const onSend = vi.fn();
    const bar = new InputBar({ onSend });
    const ta = getTextarea(bar);
    ta.value = '  Hello  ';
    ta.dispatchEvent(new Event('input'));
    getSendBtn(bar).click();
    expect(onSend).toHaveBeenCalledWith('Hello');
    expect(ta.value).toBe('');
  });

  it('Enter key submits the message', () => {
    const onSend = vi.fn();
    const bar = new InputBar({ onSend });
    const ta = getTextarea(bar);
    ta.value = 'Test';
    ta.dispatchEvent(new Event('input'));
    ta.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
    expect(onSend).toHaveBeenCalledWith('Test');
  });

  it('Shift+Enter does not submit', () => {
    const onSend = vi.fn();
    const bar = new InputBar({ onSend });
    const ta = getTextarea(bar);
    ta.value = 'Test';
    ta.dispatchEvent(new Event('input'));
    ta.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, bubbles: true }),
    );
    expect(onSend).not.toHaveBeenCalled();
  });

  it('does not submit if textarea is empty', () => {
    const onSend = vi.fn();
    const bar = new InputBar({ onSend });
    getSendBtn(bar).click();
    expect(onSend).not.toHaveBeenCalled();
  });

  it('counter is hidden below 3200 characters', () => {
    const bar = makeInputBar();
    const ta = getTextarea(bar);
    ta.value = 'a'.repeat(100);
    ta.dispatchEvent(new Event('input'));
    expect(getCounter(bar).hidden).toBe(true);
  });

  it('counter is visible above 3200 characters', () => {
    const bar = makeInputBar();
    const ta = getTextarea(bar);
    ta.value = 'a'.repeat(3_201);
    ta.dispatchEvent(new Event('input'));
    expect(getCounter(bar).hidden).toBe(false);
  });

  it('counter shows remaining characters', () => {
    const bar = makeInputBar();
    const ta = getTextarea(bar);
    ta.value = 'a'.repeat(3_900);
    ta.dispatchEvent(new Event('input'));
    expect(getCounter(bar).textContent).toContain('100 characters remaining');
  });

  it('offline: send button stays disabled after setSendDisabled(true) even after re-enable then re-disable', () => {
    const bar = makeInputBar();
    const ta = getTextarea(bar);
    ta.value = 'text';
    ta.dispatchEvent(new Event('input'));

    bar.setSendDisabled(true);
    expect(getSendBtn(bar).disabled).toBe(true);

    bar.setSendDisabled(false);
    expect(getSendBtn(bar).disabled).toBe(false);

    bar.setSendDisabled(true);
    expect(getSendBtn(bar).disabled).toBe(true);
  });
});
