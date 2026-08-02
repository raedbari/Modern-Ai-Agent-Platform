import { describe, it, expect } from 'vitest';
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

  it('has aria-live="polite"', () => {
    const list = new MessageList();
    expect(list.element.getAttribute('aria-live')).toBe('polite');
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
});
