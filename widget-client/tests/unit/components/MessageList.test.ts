import { describe, it, expect, vi } from 'vitest';
import { MessageList } from '../../../src/components/MessageList.js';
import type { Message } from '../../../src/state/types.js';

function makeMsg(overrides: Partial<Message>): Message {
  return {
    id: 'msg-1',
    role: 'user',
    text: 'Hello',
    streaming: false,
    isError: false,
    timestamp: Date.now(),
    ...overrides,
  };
}

describe('MessageList', () => {
  it('has role="log" for screen reader accessibility', () => {
    const list = new MessageList();
    expect(list.element.getAttribute('role')).toBe('log');
  });

  it('does not announce every incremental text update', () => {
    const list = new MessageList();
    expect(list.element.getAttribute('aria-live')).toBeNull();
  });

  it('renders messages after update()', () => {
    const list = new MessageList();
    list.update([makeMsg({ id: 'm1', text: 'First' }), makeMsg({ id: 'm2', text: 'Second' })]);
    const bubbles = list.element.querySelectorAll('.message-bubble');
    expect(bubbles).toHaveLength(2);
  });

  it('removes messages that are no longer present', () => {
    const list = new MessageList();
    list.update([makeMsg({ id: 'm1' }), makeMsg({ id: 'm2' })]);
    list.update([makeMsg({ id: 'm1' })]);
    expect(list.element.querySelectorAll('.message-bubble')).toHaveLength(1);
  });

  it('does not re-create bubbles for existing messages', () => {
    const list = new MessageList();
    list.update([makeMsg({ id: 'm1', text: 'Original' })]);
    const bubble = list.element.querySelector('.message-bubble');
    list.update([makeMsg({ id: 'm1', text: 'Updated' })]);
    // Same DOM element should still be in place (no re-creation)
    expect(list.element.querySelector('.message-bubble')).toBe(bubble);
  });

  it('updates text of an existing bubble when content changes', () => {
    const list = new MessageList();
    list.update([makeMsg({ id: 'm1', text: 'Original' })]);
    list.update([makeMsg({ id: 'm1', text: 'Updated' })]);
    const span = list.element.querySelector('.message-bubble__text');
    expect(span?.textContent).toBe('Updated');
  });

  it('does not steal scroll position while the reader is viewing history', () => {
    const list = new MessageList();
    const animationSpy = vi
      .spyOn(window, 'requestAnimationFrame')
      .mockImplementation(() => 1);
    Object.defineProperties(list.element, {
      scrollHeight: { configurable: true, value: 1_000 },
      clientHeight: { configurable: true, value: 300 },
    });
    list.element.scrollTop = 100;

    list.update([makeMsg({ id: 'm1', text: 'New message' })]);

    expect(animationSpy).not.toHaveBeenCalled();
    expect(list.element.scrollTop).toBe(100);
    animationSpy.mockRestore();
  });
});
