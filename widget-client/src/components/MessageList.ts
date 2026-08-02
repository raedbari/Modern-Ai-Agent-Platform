import type { Message } from '../state/types.js';
import { MessageBubble } from './MessageBubble.js';

/**
 * MessageList — scrollable container for chat messages.
 *
 * Accessibility:
 *  - role="log" semantics (an ordered list of messages)
 *  - aria-live="polite" for assistant streaming updates
 *  - Auto-scrolls to the bottom when new messages arrive
 */
export class MessageList {
  readonly #root: HTMLElement;
  readonly #inner: HTMLElement;
  #bubbles: Map<string, MessageBubble> = new Map();

  constructor() {
    this.#root = document.createElement('div');
    this.#root.className = 'message-list';
    this.#root.setAttribute('role', 'log');
    this.#root.setAttribute('aria-live', 'polite');
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

    this.#scrollToBottom();
  }

  #scrollToBottom(): void {
    // requestAnimationFrame ensures DOM has been painted before scrolling
    requestAnimationFrame(() => {
      this.#root.scrollTop = this.#root.scrollHeight;
    });
  }

  static styles(): string {
    return `
      .message-list {
        flex: 1;
        overflow-y: auto;
        padding: 1rem 0.9rem 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 0.65rem;
        scrollbar-color: var(--wc-border, #cbd5e1) transparent;
        scroll-behavior: smooth;
      }
      .message-list-inner {
        display: flex;
        flex-direction: column;
        gap: 0.65rem;
      }
    `;
  }
}
