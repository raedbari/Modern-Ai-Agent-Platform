export type DirectionMode = 'ltr' | 'rtl' | 'auto';

export interface DirectionControllerOptions {
  mode?: DirectionMode;
  onChange(direction: 'ltr' | 'rtl'): void;
}

/**
 * DirectionController — detects and observes text direction changes.
 *
 * Sourcing strategy:
 *  1. If mode is "ltr" or "rtl", use explicit mode.
 *  2. If mode is "auto", inspect `document.documentElement.dir` or `document.body.dir`.
 *  3. Uses `MutationObserver` on `document.documentElement` to react dynamically to changes.
 */
export class DirectionController {
  #mode: DirectionMode;
  #onChange: (direction: 'ltr' | 'rtl') => void;
  #observer: MutationObserver | null = null;
  #currentDirection: 'ltr' | 'rtl' = 'ltr';

  constructor(options: DirectionControllerOptions) {
    this.#mode = options.mode ?? 'auto';
    this.#onChange = options.onChange;
    this.#update();

    if (this.#mode === 'auto' && typeof MutationObserver !== 'undefined') {
      this.#observer = new MutationObserver(() => this.#update());
      this.#observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['dir', 'lang'],
      });
    }
  }

  get direction(): 'ltr' | 'rtl' {
    return this.#currentDirection;
  }

  setMode(mode: DirectionMode): void {
    this.#mode = mode;
    if (this.#mode !== 'auto' && this.#observer) {
      this.#observer.disconnect();
      this.#observer = null;
    } else if (this.#mode === 'auto' && !this.#observer && typeof MutationObserver !== 'undefined') {
      this.#observer = new MutationObserver(() => this.#update());
      this.#observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['dir', 'lang'],
      });
    }
    this.#update();
  }

  disconnect(): void {
    if (this.#observer) {
      this.#observer.disconnect();
      this.#observer = null;
    }
  }

  #update(): void {
    let resolved: 'ltr' | 'rtl' = 'ltr';

    if (this.#mode === 'rtl' || this.#mode === 'ltr') {
      resolved = this.#mode;
    } else {
      const pageDir = (
        document.documentElement.getAttribute('dir') ||
        document.body?.getAttribute('dir') ||
        ''
      ).toLowerCase();

      resolved = pageDir === 'rtl' ? 'rtl' : 'ltr';
    }

    if (resolved !== this.#currentDirection) {
      this.#currentDirection = resolved;
      this.#onChange(resolved);
    }
  }
}
