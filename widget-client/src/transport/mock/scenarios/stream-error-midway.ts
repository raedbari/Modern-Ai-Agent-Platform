import type { MessageCallbacks } from '../../types.js';

/**
 * Stream-error-midway scenario: sends 3 chunks then triggers an error.
 * Returns a cancel function.
 */
export function runStreamErrorMidway(callbacks: MessageCallbacks): () => void {
  const chunks = ['Processing your request', '... working ', '... almost done'];
  let cancelled = false;
  let index = 0;

  function sendNext(): void {
    if (cancelled) return;

    if (index < chunks.length) {
      callbacks.onChunk(chunks[index++]);
      setTimeout(sendNext, 50);
    } else {
      callbacks.onError({
        code: 'STREAM_INTERRUPTED',
        message: 'The response stream was interrupted unexpectedly.',
        retryable: true,
      });
    }
  }

  setTimeout(sendNext, 50);

  return () => {
    cancelled = true;
  };
}
