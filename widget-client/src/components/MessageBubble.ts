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
        max-inline-size: min(82%, 19rem);
        padding: 0.68rem 0.9rem;
        border: 1px solid transparent;
        border-radius: 1.1rem;
        font-size: 0.9rem;
        line-height: 1.55;
        overflow-wrap: anywhere;
        white-space: pre-wrap;
      }
      .message-bubble--user {
        align-self: flex-end;
        border-end-end-radius: 0.35rem;
        background: var(--wc-user-bubble-bg, #2563eb);
        color: var(--wc-on-primary, #fff);
        box-shadow: 0 5px 14px rgba(15, 23, 42, 0.1);
      }
      .message-bubble--assistant {
        align-self: flex-start;
        border-color: var(--wc-border, #e2e8f0);
        border-end-start-radius: 0.35rem;
        background: var(--wc-assistant-bubble-bg, #f1f5f9);
        color: var(--wc-body-text, #0f172a);
      }
      .message-bubble--streaming::after {
        content: '▋';
        display: inline-block;
        animation: blink 1s step-end infinite;
      }
      .message-bubble--error {
        border-color: var(--wc-error-text, #b91c1c);
        background: var(--wc-error-surface, #fee2e2);
        color: var(--wc-error-text, #b91c1c);
      }
      @keyframes blink {
        50% { opacity: 0; }
      }
      @media (prefers-reduced-motion: reduce) {
        .message-bubble--streaming::after { animation: none; }
      }
    `;
  }
}
