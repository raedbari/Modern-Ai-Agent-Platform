import type { MessageCallbacks } from '../../types.js';

/**
 * Error-response scenario: immediately calls onError without any chunks.
 * Returns a no-op cancel function.
 */
export function runErrorResponse(callbacks: MessageCallbacks): () => void {
  // Use a microtask so the caller always receives the cancel function first
  queueMicrotask(() => {
    callbacks.onError({
      code: 'AGENT_UNAVAILABLE',
      message: 'The agent is currently unavailable. Please try again later.',
      retryable: true,
    });
  });

  return () => {
    // Nothing to cancel — error is immediate
  };
}
