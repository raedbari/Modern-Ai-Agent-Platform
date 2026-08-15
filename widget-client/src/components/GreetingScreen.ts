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
}
