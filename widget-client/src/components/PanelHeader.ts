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
  readonly #avatarEl: HTMLElement;
  readonly #callbacks: PanelHeaderCallbacks;

  constructor(callbacks: PanelHeaderCallbacks, title = 'Chat support') {
    this.#callbacks = callbacks;
    this.#root = document.createElement('header');
    this.#root.className = 'panel-header';

    const identity = document.createElement('div');
    identity.className = 'panel-header__identity';

    this.#avatarEl = document.createElement('span');
    this.#avatarEl.className = 'panel-header__avatar';
    this.#avatarEl.setAttribute('aria-hidden', 'true');
    this.#avatarEl.textContent = initialsFor(title);

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
    identity.appendChild(this.#avatarEl);
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
    this.#avatarEl.textContent = initialsFor(title);
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
}

function initialsFor(title: string): string {
  const words = title.trim().split(/\s+/u).filter(Boolean);
  if (words.length === 0) return 'AI';
  return words
    .slice(0, 2)
    .map((word) => Array.from(word)[0] ?? '')
    .join('')
    .toLocaleUpperCase();
}
