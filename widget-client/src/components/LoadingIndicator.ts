/**
 * LoadingIndicator — animated dots shown while the assistant is typing.
 *
 * Accessibility:
 *  - role="status" announces state to screen readers non-intrusively
 *  - aria-label provides a meaningful description
 *  - aria-hidden dots prevent redundant announcements
 */
export class LoadingIndicator {
  readonly #root: HTMLElement;

  constructor(label = 'Assistant is typing') {
    this.#root = document.createElement('div');
    this.#root.className = 'loading-indicator';
    this.#root.setAttribute('role', 'status');
    this.#root.setAttribute('aria-label', label);
    this.#root.hidden = true;

    // Three animated dots (purely decorative)
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement('span');
      dot.className = 'loading-indicator__dot';
      dot.setAttribute('aria-hidden', 'true');
      this.#root.appendChild(dot);
    }
  }

  get element(): HTMLElement {
    return this.#root;
  }

  show(): void {
    this.#root.hidden = false;
  }

  hide(): void {
    this.#root.hidden = true;
  }

  static styles(): string {
    return `
      .loading-indicator {
        display: flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.5rem 0.75rem;
        align-self: flex-start;
      }
      .loading-indicator__dot {
        inline-size: 0.45rem;
        block-size: 0.45rem;
        border-radius: 50%;
        background: var(--wc-primary, #2563eb);
        opacity: 0.6;
        animation: bounce 1.2s ease-in-out infinite;
      }
      .loading-indicator__dot:nth-child(2) {
        animation-delay: 0.2s;
      }
      .loading-indicator__dot:nth-child(3) {
        animation-delay: 0.4s;
      }
      @keyframes bounce {
        0%, 80%, 100% { transform: translateY(0); }
        40%            { transform: translateY(-0.4rem); }
      }
      @media (prefers-reduced-motion: reduce) {
        .loading-indicator__dot { animation: none; }
      }
    `;
  }
}
