export interface LauncherCallbacks {
  onClick(): void;
}

/**
 * Launcher — the floating button that opens/closes the chat panel.
 *
 * Requirements:
 *  - part="launcher-button" for host CSS customisation
 *  - aria-label from config launcherLabel
 *  - aria-expanded tracks panel open/closed state
 *  - Touch target minimum 44px x 44px (WCAG 2.1 AA)
 *  - Uses CSS logical properties for positioning
 */
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

    const icon = document.createElement('span');
    icon.className = 'launcher-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = '💬';

    this.#button.appendChild(icon);
    this.#button.addEventListener('click', () => this.#callbacks.onClick());
  }

  get element(): HTMLButtonElement {
    return this.#button;
  }

  /** Update aria-expanded state to reflect whether panel is open */
  setExpanded(expanded: boolean): void {
    this.#button.setAttribute('aria-expanded', String(expanded));
  }

  /** Update label dynamically if setConfig changes launcherLabel */
  setLabel(label: string): void {
    this.#button.setAttribute('aria-label', label);
  }

  static styles(): string {
    return `
      .launcher-button {
        inline-size: 3.5rem;
        block-size: 3.5rem;
        min-inline-size: 44px;
        min-block-size: 44px;
        border-radius: 50%;
        border: none;
        background: var(--wc-launcher-bg, var(--wc-primary, #6366f1));
        color: #ffffff;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.16);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }
      .launcher-button:hover {
        transform: scale(1.06);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.22);
      }
      .launcher-button:focus-visible {
        outline: 2px solid var(--wc-primary, #6366f1);
        outline-offset: 3px;
      }
      .launcher-icon {
        font-size: 1.5rem;
        line-height: 1;
      }
    `;
  }
}
