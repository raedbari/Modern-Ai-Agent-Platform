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
}
