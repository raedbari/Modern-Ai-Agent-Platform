import type { ConnectionStatus } from '../transport/types.js';
import { createIcon, ICON_PATHS } from '../utils/icons.js';

export interface LauncherCallbacks {
  onClick(): void;
}

/** Accessible, bubble-shaped launcher with deterministic SVG icons. */
export class Launcher {
  readonly #button: HTMLButtonElement;
  readonly #callbacks: LauncherCallbacks;

  constructor(callbacks: LauncherCallbacks, launcherLabel = 'Open chat') {
    this.#callbacks = callbacks;
    this.#button = document.createElement('button');
    this.#button.className = 'launcher-button';
    this.#button.type = 'button';
    this.#button.setAttribute('part', 'launcher-button');
    this.#button.setAttribute('aria-label', launcherLabel);
    this.#button.setAttribute('aria-expanded', 'false');
    this.#button.setAttribute('data-status', 'disconnected');

    this.#button.appendChild(createIcon('launcher-icon launcher-icon--chat', [...ICON_PATHS.chat]));
    this.#button.appendChild(createIcon('launcher-icon launcher-icon--close', [...ICON_PATHS.close]));
    this.#button.addEventListener('click', () => this.#callbacks.onClick());
  }

  get element(): HTMLButtonElement {
    return this.#button;
  }

  setExpanded(expanded: boolean): void {
    this.#button.setAttribute('aria-expanded', String(expanded));
  }

  setLabel(label: string): void {
    this.#button.setAttribute('aria-label', label);
  }

  setConnectionStatus(status: ConnectionStatus): void {
    this.#button.setAttribute('data-status', status);
  }

  static styles(): string {
    return `
      .launcher-button {
        position: relative;
        inline-size: 3.75rem;
        block-size: 3.75rem;
        min-inline-size: 44px;
        min-block-size: 44px;
        border: 1px solid rgba(255, 255, 255, 0.22);
        border-radius: 1.35rem;
        border-end-end-radius: 0.45rem;
        background: var(--wc-launcher-bg, var(--wc-primary, #2563eb));
        color: var(--wc-on-primary, #fff);
        cursor: pointer;
        display: grid;
        place-items: center;
        box-shadow: 0 12px 32px rgba(15, 23, 42, 0.2),
          0 6px 14px rgba(15, 23, 42, 0.18);
        transition: transform 180ms ease, box-shadow 180ms ease, border-radius 180ms ease;
        -webkit-tap-highlight-color: transparent;
      }
      :host([data-position='left']) .launcher-button {
        border-end-end-radius: 1.35rem;
        border-end-start-radius: 0.45rem;
      }
      .launcher-button::after {
        content: '';
        position: absolute;
        inset-block-start: 0.15rem;
        inset-inline-end: 0.15rem;
        inline-size: 0.65rem;
        block-size: 0.65rem;
        border: 2px solid var(--wc-surface, #fff);
        border-radius: 999px;
        background: #22c55e;
        opacity: 0;
        transform: scale(0.65);
        transition: opacity 180ms ease, transform 180ms ease;
      }
      .launcher-button[data-status='connected']::after {
        opacity: 1;
        transform: scale(1);
      }
      .launcher-button:hover {
        transform: translateY(-2px) scale(1.025);
        box-shadow: 0 16px 38px rgba(15, 23, 42, 0.24),
          0 8px 18px rgba(15, 23, 42, 0.2);
      }
      .launcher-button:active {
        transform: translateY(0) scale(0.98);
      }
      .launcher-button:focus-visible {
        outline: 3px solid var(--wc-primary, #2563eb);
        outline-offset: 3px;
      }
      .launcher-icon {
        position: absolute;
        inline-size: 1.65rem;
        block-size: 1.65rem;
        transition: opacity 160ms ease, transform 180ms ease;
      }
      .launcher-icon--close {
        opacity: 0;
        transform: rotate(-45deg) scale(0.7);
      }
      .launcher-button[aria-expanded='true'] {
        border-radius: 999px;
      }
      .launcher-button[aria-expanded='true'] .launcher-icon--chat {
        opacity: 0;
        transform: rotate(45deg) scale(0.7);
      }
      .launcher-button[aria-expanded='true'] .launcher-icon--close {
        opacity: 1;
        transform: rotate(0) scale(1);
      }
      @media (prefers-reduced-motion: reduce) {
        .launcher-button,
        .launcher-icon,
        .launcher-button::after {
          transition: none;
        }
      }
    `;
  }
}
