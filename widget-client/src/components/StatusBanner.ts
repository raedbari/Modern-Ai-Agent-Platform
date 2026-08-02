export type StatusVariant = 'offline' | 'error' | 'none';

/**
 * StatusBanner — displays connection/error status at the top of the chat panel.
 *
 * Accessibility:
 *  - role="status" with aria-live="assertive" for urgent announcements
 *  - Supports "offline" and "error" variants, or is hidden when variant is "none"
 */
export class StatusBanner {
  readonly #root: HTMLElement;
  readonly #textEl: HTMLElement;
  #variant: StatusVariant = 'none';

  constructor() {
    this.#root = document.createElement('div');
    this.#root.className = 'status-banner';
    this.#root.setAttribute('role', 'status');
    this.#root.setAttribute('aria-live', 'assertive');
    this.#root.setAttribute('aria-atomic', 'true');
    this.#root.hidden = true;

    this.#textEl = document.createElement('span');
    this.#textEl.className = 'status-banner__text';
    this.#root.appendChild(this.#textEl);
  }

  get element(): HTMLElement {
    return this.#root;
  }

  get variant(): StatusVariant {
    return this.#variant;
  }

  /** Show the banner with the provided variant and optional custom message. */
  show(variant: 'offline' | 'error', message?: string): void {
    this.#variant = variant;
    this.#root.hidden = false;
    this.#root.className = `status-banner status-banner--${variant}`;
    this.#textEl.textContent = message ?? this.#defaultMessage(variant);
  }

  hide(): void {
    this.#variant = 'none';
    this.#root.hidden = true;
    this.#textEl.textContent = '';
  }

  #defaultMessage(variant: 'offline' | 'error'): string {
    return variant === 'offline'
      ? 'You are offline. Messages will be sent when you reconnect.'
      : 'An error occurred. Please try again.';
  }

  static styles(): string {
    return `
      .status-banner {
        padding: 0.4rem 1rem;
        font-size: 0.8rem;
        font-weight: 500;
        text-align: center;
      }
      .status-banner--offline {
        background: #fef9c3;
        color: #92400e;
      }
      .status-banner--error {
        background: #fee2e2;
        color: #dc2626;
      }
    `;
  }
}
