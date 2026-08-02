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
}
