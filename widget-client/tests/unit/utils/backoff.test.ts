import { describe, it, expect } from 'vitest';
import { ExponentialBackoff } from '../../../src/utils/backoff.js';

describe('ExponentialBackoff', () => {
  it('starts at initial delay (1000 ms)', () => {
    const backoff = new ExponentialBackoff();
    expect(backoff.nextDelay()).toBe(1_000);
  });

  it('doubles delay on subsequent attempts', () => {
    const backoff = new ExponentialBackoff();
    expect(backoff.nextDelay()).toBe(1_000); // attempt 1
    expect(backoff.nextDelay()).toBe(2_000); // attempt 2
    expect(backoff.nextDelay()).toBe(4_000); // attempt 3
    expect(backoff.nextDelay()).toBe(8_000); // attempt 4
    expect(backoff.nextDelay()).toBe(16_000); // attempt 5
  });

  it('caps delay at maxDelayMs (30000 ms)', () => {
    const backoff = new ExponentialBackoff({ initialDelayMs: 10_000, maxDelayMs: 25_000 });
    expect(backoff.nextDelay()).toBe(10_000); // 10k
    expect(backoff.nextDelay()).toBe(20_000); // 20k
    expect(backoff.nextDelay()).toBe(25_000); // capped at 25k
  });

  it('returns null after maxAttempts (5)', () => {
    const backoff = new ExponentialBackoff({ maxAttempts: 3 });
    expect(backoff.nextDelay()).toBe(1_000);
    expect(backoff.nextDelay()).toBe(2_000);
    expect(backoff.nextDelay()).toBe(4_000);
    expect(backoff.nextDelay()).toBeNull();
    expect(backoff.hasNext).toBe(false);
  });

  it('reset() resets attempts counter to 0', () => {
    const backoff = new ExponentialBackoff();
    backoff.nextDelay();
    backoff.nextDelay();
    expect(backoff.attempts).toBe(2);

    backoff.reset();
    expect(backoff.attempts).toBe(0);
    expect(backoff.nextDelay()).toBe(1_000);
  });
});
