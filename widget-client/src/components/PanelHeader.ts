import type { ConnectionStatus } from '../transport/types.js';
import { createIcon, ICON_PATHS } from '../utils/icons.js';

export interface PanelHeaderCallbacks {
  onClose(): void;
}

/** Branded panel header populated from trusted bootstrap configuration. */
export class PanelHeader {
  readonly #root: HTMLElement;
  readonly #titleEl: HTMLElement;
  readonly #statusEl: HTMLElement;
  readonly #callbacks: PanelHeaderCallbacks;

  constructor(callbacks: PanelHeaderCallbacks, title = 'Chat support') {
    this.#callbacks = callbacks;
    this.#root = document.createElement('header');
    this.#root.className = 'panel-header';

    const identity = document.createElement('div');
    identity.className = 'panel-header__identity';

    const avatar = document.createElement('span');
    avatar.className = 'panel-header__avatar';
    avatar.appendChild(createIcon('panel-header__avatar-icon', [...ICON_PATHS.sparkle]));

    const text = document.createElement('div');
    text.className = 'panel-header__text';
    this.#titleEl = document.createElement('h2');
    this.#titleEl.className = 'panel-header__title';
    this.#titleEl.id = 'panel-title';
    this.#titleEl.textContent = title;
    this.#statusEl = document.createElement('span');
    this.#statusEl.className = 'panel-header__status';
    this.#statusEl.textContent = 'Connecting…';
    text.appendChild(this.#titleEl);
    text.appendChild(this.#statusEl);
    identity.appendChild(avatar);
    identity.appendChild(text);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'panel-header__close';
    closeBtn.type = 'button';
    closeBtn.setAttribute('aria-label', 'Close chat panel');
    closeBtn.appendChild(createIcon('panel-header__close-icon', [...ICON_PATHS.close]));
    closeBtn.addEventListener('click', () => this.#callbacks.onClose());

    this.#root.appendChild(identity);
    this.#root.appendChild(closeBtn);
  }

  get element(): HTMLElement {
    return this.#root;
  }

  setTitle(title: string): void {
    this.#titleEl.textContent = title;
  }

  setConnectionStatus(status: ConnectionStatus): void {
    const labels: Record<ConnectionStatus, string> = {
      connecting: 'Connecting…',
      connected: 'Online',
      disconnected: 'Offline',
      error: 'Unavailable',
    };
    this.#statusEl.textContent = labels[status];
    this.#statusEl.setAttribute('data-status', status);
  }

  static styles(): string {
    return `
      .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-block-size: 4.75rem;
        padding: 0.8rem 0.9rem 0.8rem 1rem;
        background: var(--wc-header-bg, var(--wc-primary, #2563eb));
        color: var(--wc-on-primary, #fff);
      }
      .panel-header__identity {
        min-inline-size: 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
      }
      .panel-header__avatar {
        inline-size: 2.55rem;
        block-size: 2.55rem;
        flex: 0 0 auto;
        display: grid;
        place-items: center;
        border: 1px solid rgba(255, 255, 255, 0.28);
        border-radius: 0.9rem;
        background: rgba(255, 255, 255, 0.14);
      }
      .panel-header__avatar-icon {
        inline-size: 1.35rem;
        block-size: 1.35rem;
      }
      .panel-header__text {
        min-inline-size: 0;
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
      }
      .panel-header__title {
        overflow: hidden;
        margin: 0;
        font-size: 0.98rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .panel-header__status {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.74rem;
        opacity: 0.86;
      }
      .panel-header__status::before {
        content: '';
        inline-size: 0.42rem;
        block-size: 0.42rem;
        border-radius: 999px;
        background: currentColor;
      }
      .panel-header__status[data-status='connected']::before {
        background: #4ade80;
      }
      .panel-header__close {
        inline-size: 2.75rem;
        block-size: 2.75rem;
        flex: 0 0 auto;
        display: grid;
        place-items: center;
        border: none;
        border-radius: 0.85rem;
        background: transparent;
        color: inherit;
        cursor: pointer;
        transition: background 150ms ease;
      }
      .panel-header__close:hover {
        background: rgba(255, 255, 255, 0.16);
      }
      .panel-header__close:focus-visible {
        outline: 2px solid currentColor;
        outline-offset: -2px;
      }
      .panel-header__close-icon {
        inline-size: 1.2rem;
        block-size: 1.2rem;
      }
    `;
  }
}
