import type { Message } from '../state/types.js';

/**
 * MessageBubble — renders a single chat message.
 *
 * Security: uses only textContent — never innerHTML — to prevent XSS.
 * Exposes `part="message-bubble"` for host-page CSS customisation.
 */
export class MessageBubble {
  readonly #root: HTMLElement;
  readonly #textEl: HTMLElement;

  constructor(message: Message) {
    this.#root = document.createElement('div');
    this.#root.className = `message-bubble message-bubble--${message.role}`;
    this.#root.setAttribute('part', 'message-bubble');
    this.#root.setAttribute('data-role', message.role);
    this.#root.setAttribute('data-id', message.id);

    this.#textEl = document.createElement('span');
    this.#textEl.className = 'message-bubble__text';
    this.#textEl.textContent = message.text; // SAFE: textContent only

    if (message.isError) {
      this.#root.classList.add('message-bubble--error');
    }
    if (message.streaming) {
      this.#root.classList.add('message-bubble--streaming');
    }

    this.#root.appendChild(this.#textEl);
  }

  get element(): HTMLElement {
    return this.#root;
  }

  /** Update the bubble's visible text and streaming/error states. */
  update(message: Message): void {
    this.#textEl.textContent = message.text; // SAFE: textContent only
    this.#root.classList.toggle('message-bubble--streaming', message.streaming);
    this.#root.classList.toggle('message-bubble--error', message.isError);
  }

  static styles(): string {
    return `
      .message-bubble {
        max-inline-size: 75%;
        padding: 0.6rem 0.9rem;
        border-radius: 1rem;
        font-size: 0.9rem;
        line-height: 1.5;
        word-break: break-word;
      }
      .message-bubble--user {
        align-self: flex-end;
        background: var(--wc-user-bubble-bg, #6366f1);
        color: #fff;
        border-end-inline-end-radius: 0.25rem;
      }
      .message-bubble--assistant {
        align-self: flex-start;
        background: #f1f5f9;
        color: var(--wc-text, #1e1e2e);
        border-end-inline-start-radius: 0.25rem;
      }
      .message-bubble--streaming::after {
        content: '▋';
        display: inline-block;
        animation: blink 1s step-end infinite;
      }
      .message-bubble--error {
        background: #fee2e2;
        color: #dc2626;
      }
      @keyframes blink {
        50% { opacity: 0; }
      }
    `;
  }
}
