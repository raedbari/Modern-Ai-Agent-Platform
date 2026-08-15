export interface BackoffOptions {
  initialDelayMs?: number; // default 1000
  multiplier?: number; // default 2
  maxDelayMs?: number; // default 30000
  maxAttempts?: number; // default 5
}

/**
 * ExponentialBackoff — utility for retrying operations with capped exponential delay.
 */
export class ExponentialBackoff {
  readonly #initialDelayMs: number;
  readonly #multiplier: number;
  readonly #maxDelayMs: number;
  readonly #maxAttempts: number;
  #attempts = 0;

  constructor(options: BackoffOptions = {}) {
    this.#initialDelayMs = options.initialDelayMs ?? 1_000;
    this.#multiplier = options.multiplier ?? 2;
    this.#maxDelayMs = options.maxDelayMs ?? 30_000;
    this.#maxAttempts = options.maxAttempts ?? 5;
  }

  get attempts(): number {
    return this.#attempts;
  }

  get hasNext(): boolean {
    return this.#attempts < this.#maxAttempts;
  }

  nextDelay(): number | null {
    if (!this.hasNext) return null;

    const delay = Math.min(
      this.#initialDelayMs * Math.pow(this.#multiplier, this.#attempts),
      this.#maxDelayMs,
    );
    this.#attempts++;
    return delay;
  }

  reset(): void {
    this.#attempts = 0;
  }
}
