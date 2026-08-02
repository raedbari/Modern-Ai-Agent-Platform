const FOCUSABLE_SELECTOR = `
  a[href],
  button:not([disabled]),
  textarea:not([disabled]),
  input:not([disabled]),
  select:not([disabled]),
  [tabindex]:not([tabindex="-1"])
`;

export class FocusTrap {
  #container: HTMLElement | null = null;
  #onEscape: (() => void) | null = null;
  #previouslyFocused: HTMLElement | null = null;
  #keydownHandler = (e: KeyboardEvent) => this.#handleKeydown(e);

  activate(container: HTMLElement, onEscape?: () => void): void {
    this.deactivate(); // ensure clean state

    this.#container = container;
    this.#onEscape = onEscape ?? null;
    this.#previouslyFocused = (document.activeElement as HTMLElement) ?? null;

    document.addEventListener('keydown', this.#keydownHandler, true);

    // Focus the first focusable element
    this.focusFirst();
  }

  deactivate(): void {
    if (!this.#container) return;

    document.removeEventListener('keydown', this.#keydownHandler, true);

    // Restore focus to previously focused element
    if (this.#previouslyFocused && typeof this.#previouslyFocused.focus === 'function') {
      this.#previouslyFocused.focus();
    }

    this.#container = null;
    this.#onEscape = null;
    this.#previouslyFocused = null;
  }

  focusFirst(): void {
    const focusables = this.#getFocusableElements();
    if (focusables.length > 0) {
      focusables[0].focus();
    } else if (this.#container) {
      this.#container.focus();
    }
  }

  #getFocusableElements(): HTMLElement[] {
    if (!this.#container) return [];
    const elements = Array.from(
      this.#container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
    );
    return elements.filter(
      (el) => el.offsetParent !== null || el.getClientRects().length > 0 || el.tabIndex >= 0,
    );
  }

  #handleKeydown(e: KeyboardEvent): void {
    if (!this.#container) return;

    if (e.key === 'Escape') {
      e.stopPropagation();
      e.preventDefault();
      this.#onEscape?.();
      return;
    }

    if (e.key === 'Tab') {
      const focusables = this.#getFocusableElements();
      if (focusables.length === 0) {
        e.preventDefault();
        return;
      }

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = (this.#container.shadowRoot?.activeElement ||
        document.activeElement) as HTMLElement;

      if (e.shiftKey) {
        // Shift + Tab: if on first element, wrap to last
        if (active === first || !this.#container.contains(active)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        // Tab: if on last element, wrap to first
        if (active === last || !this.#container.contains(active)) {
          e.preventDefault();
          first.focus();
        }
      }
    }
  }
}
