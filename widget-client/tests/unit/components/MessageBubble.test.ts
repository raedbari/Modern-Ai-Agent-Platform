import { describe, it, expect } from 'vitest';
import { MessageBubble } from '../../../src/components/MessageBubble.js';
import type { Message } from '../../../src/state/types.js';

function makeMsg(overrides: Partial<Message> = {}): Message {
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

describe('MessageBubble', () => {
  it('has part="message-bubble" attribute', () => {
    const bubble = new MessageBubble(makeMsg());
    expect(bubble.element.getAttribute('part')).toBe('message-bubble');
  });

  it('sets data-role from message role', () => {
    const bubble = new MessageBubble(makeMsg({ role: 'assistant' }));
    expect(bubble.element.getAttribute('data-role')).toBe('assistant');
  });

  it('renders message text via textContent', () => {
    const bubble = new MessageBubble(makeMsg({ text: 'Hi there' }));
    const span = bubble.element.querySelector('.message-bubble__text');
    expect(span?.textContent).toBe('Hi there');
  });

  it('XSS: script tag is rendered as literal text, not executed', () => {
    const xss = '<img src=x onerror="alert(1)">';
    const bubble = new MessageBubble(makeMsg({ text: xss }));
    const span = bubble.element.querySelector('.message-bubble__text');
    // textContent should equal the raw string; no HTML should be parsed
    expect(span?.textContent).toBe(xss);
    // The span's innerHTML should be the HTML-escaped version
    expect(span?.innerHTML).not.toContain('<img');
  });

  it('adds streaming class when message is streaming', () => {
    const bubble = new MessageBubble(makeMsg({ streaming: true }));
    expect(bubble.element.classList.contains('message-bubble--streaming')).toBe(true);
  });

  it('adds error class when message has error', () => {
    const bubble = new MessageBubble(makeMsg({ isError: true }));
    expect(bubble.element.classList.contains('message-bubble--error')).toBe(true);
  });

  it('update() changes text content', () => {
    const bubble = new MessageBubble(makeMsg({ text: 'Old' }));
    bubble.update(makeMsg({ text: 'New' }));
    expect(bubble.element.querySelector('.message-bubble__text')?.textContent).toBe('New');
  });

  it('update() toggles streaming class', () => {
    const bubble = new MessageBubble(makeMsg({ streaming: true }));
    bubble.update(makeMsg({ streaming: false }));
    expect(bubble.element.classList.contains('message-bubble--streaming')).toBe(false);
  });
});
