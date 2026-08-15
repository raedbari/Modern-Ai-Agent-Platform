import type { Message } from '../state/types.js';
import { MessageBubble } from './MessageBubble.js';

/**
 * MessageList — scrollable container for chat messages.
 *
 * Accessibility:
 *  - role="log" semantics (an ordered list of messages)
 *  - Completion is announced by the dedicated live region, not per character
 *  - Follows new messages only while the reader is already near the bottom
 */
export class MessageList {
  readonly #root: HTMLElement;
  readonly #inner: HTMLElement;
  #bubbles: Map<string, MessageBubble> = new Map();

  constructor() {
    this.#root = document.createElement('div');
    this.#root.className = 'message-list';
    this.#root.setAttribute('role', 'log');
    this.#root.setAttribute('aria-label', 'Conversation');

    this.#inner = document.createElement('div');
    this.#inner.className = 'message-list-inner';
    this.#root.appendChild(this.#inner);
  }

  get element(): HTMLElement {
    return this.#root;
  }

  /** Sync the rendered messages to match the provided array. */
  update(messages: Message[]): void {
    const shouldFollow = this.#isNearBottom();
    const existingIds = new Set(this.#bubbles.keys());
    const newIds = new Set(messages.map((m) => m.id));

    // Remove messages that no longer exist
    for (const id of existingIds) {
      if (!newIds.has(id)) {
        this.#bubbles.get(id)?.element.remove();
        this.#bubbles.delete(id);
      }
    }

    // Add or update messages
    for (const msg of messages) {
      if (this.#bubbles.has(msg.id)) {
        this.#bubbles.get(msg.id)!.update(msg);
      } else {
        const bubble = new MessageBubble(msg);
        this.#bubbles.set(msg.id, bubble);
        this.#inner.appendChild(bubble.element);
      }
    }

    if (shouldFollow) this.#scrollToBottom();
  }

  #isNearBottom(): boolean {
    const distance = this.#root.scrollHeight
      - this.#root.scrollTop
      - this.#root.clientHeight;
    return distance <= 48;
  }

  #scrollToBottom(): void {
    // requestAnimationFrame ensures DOM has been painted before scrolling
    requestAnimationFrame(() => {
      this.#root.scrollTop = this.#root.scrollHeight;
    });
  }
}
