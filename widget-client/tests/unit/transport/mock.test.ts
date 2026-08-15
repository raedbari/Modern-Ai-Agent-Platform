import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MockTransport } from '../../../src/transport/mock/MockTransport.js';
import type { TransportError } from '../../../src/transport/types.js';

const MSG = { text: 'Hello' };

function makeCallbacks() {
  return {
    onChunk: vi.fn<(chunk: string) => void>(),
    onDone: vi.fn<() => void>(),
    onError: vi.fn<(err: TransportError) => void>(),
  };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

/** Helper to connect MockTransport safely with fake timers */
async function connectMock(transport: MockTransport): Promise<void> {
  const p = transport.connect();
  vi.advanceTimersByTime(10);
  await p;
}

describe('MockTransport — happy-path scenario', () => {
  it('calls onChunk 5 times then onDone', async () => {
    const transport = new MockTransport('happy-path');
    await connectMock(transport);
    const cb = makeCallbacks();

    transport.send(MSG, cb);

    // Advance 5 chunks x 50ms
    vi.advanceTimersByTime(300);

    expect(cb.onChunk).toHaveBeenCalledTimes(5);
    expect(cb.onDone).toHaveBeenCalledTimes(1);
    expect(cb.onError).not.toHaveBeenCalled();
  });
});

describe('MockTransport — slow-response scenario', () => {
  it('waits 5 s before the first (and only) chunk, then calls onDone', async () => {
    const transport = new MockTransport('slow-response');
    await connectMock(transport);
    const cb = makeCallbacks();

    transport.send(MSG, cb);

    // Fast-forward less than 5 s — nothing should have fired
    vi.advanceTimersByTime(4_999);
    expect(cb.onChunk).not.toHaveBeenCalled();
    expect(cb.onDone).not.toHaveBeenCalled();

    // Now past the 5 s delay
    vi.advanceTimersByTime(1);
    expect(cb.onChunk).toHaveBeenCalledTimes(1);
    expect(cb.onDone).toHaveBeenCalledTimes(1);
  });
});

describe('MockTransport — error-response scenario', () => {
  it('immediately calls onError without any chunks', async () => {
    const transport = new MockTransport('error-response');
    await connectMock(transport);
    const cb = makeCallbacks();

    transport.send(MSG, cb);
    await Promise.resolve(); // flush microtask

    expect(cb.onChunk).not.toHaveBeenCalled();
    expect(cb.onDone).not.toHaveBeenCalled();
    expect(cb.onError).toHaveBeenCalledTimes(1);
    expect((cb.onError.mock.calls[0][0] as TransportError).retryable).toBe(true);
  });
});

describe('MockTransport — stream-error-midway scenario', () => {
  it('calls onChunk 3 times then onError', async () => {
    const transport = new MockTransport('stream-error-midway');
    await connectMock(transport);
    const cb = makeCallbacks();

    transport.send(MSG, cb);
    vi.advanceTimersByTime(300);

    expect(cb.onChunk).toHaveBeenCalledTimes(3);
    expect(cb.onDone).not.toHaveBeenCalled();
    expect(cb.onError).toHaveBeenCalledTimes(1);
  });
});

describe('MockTransport — cancel', () => {
  it('calling the cancel function stops chunk delivery', async () => {
    const transport = new MockTransport('happy-path');
    await connectMock(transport);
    const cb = makeCallbacks();

    const cancel = transport.send(MSG, cb);
    cancel(); // cancel immediately

    vi.advanceTimersByTime(300);

    // No callbacks should fire after cancellation
    expect(cb.onChunk).not.toHaveBeenCalled();
    expect(cb.onDone).not.toHaveBeenCalled();
  });
});

describe('MockTransport — disconnect safety', () => {
  it('disconnect() can be called multiple times without throwing', async () => {
    const transport = new MockTransport('happy-path');
    await connectMock(transport);

    expect(() => {
      transport.disconnect();
      transport.disconnect();
    }).not.toThrow();
  });

  it('onStatusChange receives "connecting" then "connected" on connect()', async () => {
    const transport = new MockTransport('happy-path');
    const statuses: string[] = [];
    transport.onStatusChange((s) => statuses.push(s));

    await connectMock(transport);

    expect(statuses).toEqual(['connecting', 'connected']);
  });

  it('onStatusChange receives "disconnected" after disconnect()', async () => {
    const transport = new MockTransport('happy-path');
    const statuses: string[] = [];
    transport.onStatusChange((s) => statuses.push(s));

    await connectMock(transport);
    transport.disconnect();

    expect(statuses).toContain('disconnected');
  });
});
