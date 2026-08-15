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
}
