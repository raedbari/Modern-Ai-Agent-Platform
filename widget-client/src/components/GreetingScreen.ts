/**
 * GreetingScreen — shown when no messages have been exchanged.
 *
 * Renders a welcome message inside the shadow DOM hierarchy.
 * Uses only textContent to prevent XSS.
 */
export class GreetingScreen {
  readonly #root: HTMLElement;

  constructor(welcomeMessage: string) {
    this.#root = document.createElement('div');
    this.#root.className = 'greeting-screen';
    this.#root.setAttribute('role', 'region');
    this.#root.setAttribute('aria-label', 'Welcome');

    const icon = document.createElement('div');
    icon.className = 'greeting-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = '💬';

    const msg = document.createElement('p');
    msg.className = 'greeting-message';
    msg.textContent = welcomeMessage; // textContent — safe from XSS

    this.#root.appendChild(icon);
    this.#root.appendChild(msg);
  }

  get element(): HTMLElement {
    return this.#root;
  }

  /** Update the welcome message without re-creating the element. */
  setMessage(message: string): void {
    const p = this.#root.querySelector('.greeting-message');
    if (p) p.textContent = message;
  }

  static styles(): string {
    return `
      .greeting-screen {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        padding: 2rem;
        flex: 1;
        text-align: center;
      }
      .greeting-icon {
        font-size: 2.5rem;
        line-height: 1;
      }
      .greeting-message {
        margin: 0;
        font-size: 0.95rem;
        color: var(--wc-text, #1e1e2e);
        opacity: 0.8;
      }
    `;
  }
}
