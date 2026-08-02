import type { MessageCallbacks } from '../../types.js';

/**
 * Happy-path scenario: streams 5 text chunks at 50 ms intervals, then calls onDone.
 * Returns a cancel function.
 */
export function runHappyPath(callbacks: MessageCallbacks): () => void {
  const chunks = [
    'Sure, ',
    "I'd be happy ",
    'to help you ',
    'with that! ',
    'What else can I do for you?',
  ];

  let cancelled = false;
  let index = 0;

  function sendNext(): void {
    if (cancelled || index >= chunks.length) {
      if (!cancelled) callbacks.onDone();
      return;
    }
    callbacks.onChunk(chunks[index++]);
    setTimeout(sendNext, 50);
  }

  setTimeout(sendNext, 50);

  return () => {
    cancelled = true;
  };
}
