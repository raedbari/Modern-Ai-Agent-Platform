import type { MessageCallbacks } from '../../types.js';

/**
 * Slow-response scenario: waits 5 seconds before sending the first chunk,
 * then delivers a single response and calls onDone.
 * Returns a cancel function.
 */
export function runSlowResponse(callbacks: MessageCallbacks): () => void {
  let cancelled = false;

  const timer = setTimeout(() => {
    if (cancelled) return;
    callbacks.onChunk('Sorry for the wait! Here is your answer.');
    if (!cancelled) callbacks.onDone();
  }, 5_000);

  return () => {
    cancelled = true;
    clearTimeout(timer);
  };
}
