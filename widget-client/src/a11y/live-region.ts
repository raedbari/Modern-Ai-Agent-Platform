/**
 * Programmatic helpers for accessible aria-live screen reader announcements.
 */
export class LiveRegion {
  readonly #element: HTMLElement;

  constructor(politeness: 'polite' | 'assertive' = 'polite') {
    this.#element = document.createElement('div');
    this.#element.className = 'wc-sr-only';
    this.#element.setAttribute('role', 'status');
    this.#element.setAttribute('aria-live', politeness);
    this.#element.setAttribute('aria-atomic', 'true');

    // Screen reader visually-hidden styles
    Object.assign(this.#element.style, {
      position: 'absolute',
      width: '1px',
      height: '1px',
      padding: '0',
      margin: '-1px',
      overflow: 'hidden',
      clip: 'rect(0, 0, 0, 0)',
      whiteSpace: 'nowrap',
      border: '0',
    });
  }

  get element(): HTMLElement {
    return this.#element;
  }

  announce(message: string): void {
    // Clear and set after microtask to trigger screen reader re-announcement
    this.#element.textContent = '';
    queueMicrotask(() => {
      this.#element.textContent = message;
    });
  }
}
