import { createIcon, ICON_PATHS } from '../utils/icons.js';

/** Safe greeting populated from the public bootstrap response. */
export class GreetingScreen {
  readonly #root: HTMLElement;

  constructor(welcomeMessage: string) {
    this.#root = document.createElement('div');
    this.#root.className = 'greeting-screen';
    this.#root.setAttribute('role', 'region');
    this.#root.setAttribute('aria-label', 'Welcome');

    const icon = document.createElement('div');
    icon.className = 'greeting-icon';
    icon.appendChild(createIcon('greeting-icon__svg', [...ICON_PATHS.chat]));

    const msg = document.createElement('p');
    msg.className = 'greeting-message';
    msg.textContent = welcomeMessage;
    this.#root.appendChild(icon);
    this.#root.appendChild(msg);
  }

  get element(): HTMLElement {
    return this.#root;
  }

  setMessage(message: string): void {
    const paragraph = this.#root.querySelector('.greeting-message');
    if (paragraph) paragraph.textContent = message;
  }

  static styles(): string {
    return `
      .greeting-screen {
        display: flex;
        flex: 1;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        padding: 2.25rem;
        text-align: center;
      }
      .greeting-icon {
        inline-size: 4rem;
        block-size: 4rem;
        display: grid;
        place-items: center;
        border: 1px solid var(--wc-border, #e2e8f0);
        border-radius: 1.4rem;
        background: var(--wc-surface, #fff);
        color: var(--wc-primary, #2563eb);
      }
      .greeting-icon__svg {
        inline-size: 1.8rem;
        block-size: 1.8rem;
      }
      .greeting-message {
        max-inline-size: 17rem;
        margin: 0;
        color: var(--wc-body-text, #0f172a);
        font-size: 0.96rem;
        line-height: 1.65;
        white-space: pre-wrap;
      }
    `;
  }
}
