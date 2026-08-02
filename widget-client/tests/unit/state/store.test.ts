import { describe, it, expect, vi } from 'vitest';
import { WidgetStore } from '../../../src/state/store.js';
import { rootReducer } from '../../../src/state/reducers.js';
import type { WidgetState } from '../../../src/state/types.js';

const INITIAL: WidgetState = {
  isPanelOpen: false,
  messages: [],
  connectionStatus: 'disconnected',
  direction: 'auto',
  appearance: 'light',
  configPatch: {},
};

function makeStore(): WidgetStore {
  return new WidgetStore(rootReducer, INITIAL);
}

describe('WidgetStore', () => {
  it('getState() returns the initial state', () => {
    const store = makeStore();
    expect(store.getState()).toEqual(INITIAL);
  });

  it('dispatch() updates state', () => {
    const store = makeStore();
    store.dispatch({ type: 'OPEN_PANEL' });
    expect(store.getState().isPanelOpen).toBe(true);
  });

  it('subscribe() is called after each dispatch that changes state', () => {
    const store = makeStore();
    const listener = vi.fn();
    store.subscribe(listener);
    store.dispatch({ type: 'OPEN_PANEL' });
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalledWith(expect.objectContaining({ isPanelOpen: true }));
  });

  it('subscribe() is NOT called when state is unchanged (idempotent action)', () => {
    const store = makeStore();
    const listener = vi.fn();
    store.subscribe(listener);
    // CLOSE_PANEL on already-closed panel returns same reference → no notification
    store.dispatch({ type: 'CLOSE_PANEL' });
    expect(listener).not.toHaveBeenCalled();
  });

  it('unsubscribe() stops the listener from receiving updates', () => {
    const store = makeStore();
    const listener = vi.fn();
    const unsub = store.subscribe(listener);
    unsub();
    store.dispatch({ type: 'OPEN_PANEL' });
    expect(listener).not.toHaveBeenCalled();
  });

  it('multiple subscribers all receive the update', () => {
    const store = makeStore();
    const a = vi.fn();
    const b = vi.fn();
    store.subscribe(a);
    store.subscribe(b);
    store.dispatch({ type: 'OPEN_PANEL' });
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).toHaveBeenCalledTimes(1);
  });

  it('unsubscribing one does not affect others', () => {
    const store = makeStore();
    const a = vi.fn();
    const b = vi.fn();
    const unsubA = store.subscribe(a);
    store.subscribe(b);
    unsubA();
    store.dispatch({ type: 'OPEN_PANEL' });
    expect(a).not.toHaveBeenCalled();
    expect(b).toHaveBeenCalledTimes(1);
  });
});
