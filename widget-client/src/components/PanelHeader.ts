export interface PanelHeaderCallbacks {
  onClose(): void;
}

/**
 * PanelHeader — header bar for the ChatPanel with heading and close button.
 */
export class PanelHeader {
  readonly #root: HTMLElement;
  readonly #titleEl: HTMLElement;
  readonly #callbacks: PanelHeaderCallbacks;

  constructor(callbacks: PanelHeaderCallbacks, title = 'Chat Support') {
    this.#callbacks = callbacks;

    this.#root = document.createElement('header');
    this.#root.className = 'panel-header';

    this.#titleEl = document.createElement('h2');
    this.#titleEl.className = 'panel-header__title';
    this.#titleEl.id = 'panel-title';
    this.#titleEl.textContent = title;

    const closeBtn = document.createElement('button');
    closeBtn.className = 'panel-header__close';
    closeBtn.type = 'button';
    closeBtn.setAttribute('aria-label', 'Close chat panel');
    closeBtn.textContent = '✕';
    closeBtn.addEventListener('click', () => this.#callbacks.onClose());

    this.#root.appendChild(this.#titleEl);
    this.#root.appendChild(closeBtn);
  }

  get element(): HTMLElement {
    return this.#root;
  }

  setTitle(title: string): void {
    this.#titleEl.textContent = title;
  }

  static styles(): string {
    return `
      .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 1rem;
        background: var(--wc-header-bg, var(--wc-primary, #6366f1));
        color: #ffffff;
        border-start-start-radius: 1rem;
        border-start-end-radius: 1rem;
      }
      .panel-header__title {
        margin: 0;
        font-size: 1rem;
        font-weight: 600;
      }
      .panel-header__close {
        background: none;
        border: none;
        color: inherit;
        font-size: 1.1rem;
        cursor: pointer;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        line-height: 1;
        transition: background 0.15s;
      }
      .panel-header__close:hover {
        background: rgba(255, 255, 255, 0.2);
      }
    `;
  }
}
