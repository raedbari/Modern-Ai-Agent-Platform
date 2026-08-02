import { describe, it, expect } from 'vitest';
import { MessageBubble } from '../../../src/components/MessageBubble.js';

describe('Security Verification: XSS Prevention', () => {
  it('renders script tag payload as literal text without execution', () => {
    const payload = '<script>window.XSS_EXECUTED = true;</script>';
    const bubble = new MessageBubble({
      id: '1',
      role: 'assistant',
      text: payload,
      streaming: false,
      isError: false,
      timestamp: Date.now(),
    });

    const span = bubble.element.querySelector('.message-bubble__text');
    expect(span?.textContent).toBe(payload);
    expect(span?.querySelector('script')).toBeNull();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    expect((window as any).XSS_EXECUTED).toBeUndefined();
  });

  it('renders img onerror payload safely', () => {
    const payload = '<img src="x" onerror="alert(1)">';
    const bubble = new MessageBubble({
      id: '2',
      role: 'user',
      text: payload,
      streaming: false,
      isError: false,
      timestamp: Date.now(),
    });

    const span = bubble.element.querySelector('.message-bubble__text');
    expect(span?.textContent).toBe(payload);
    expect(span?.querySelector('img')).toBeNull();
  });
});
