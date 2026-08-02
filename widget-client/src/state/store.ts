import type { WidgetState, Action } from './types.js';

const INITIAL_STATE: WidgetState = {
  isPanelOpen: false,
  messages: [],
  connectionStatus: 'disconnected',
  direction: 'auto',
  appearance: 'light',
  configPatch: {},
};

type Subscriber = (state: WidgetState) => void;

/**
 * WidgetStore — a minimal Redux-style state container.
 *
 * - `getState()` returns a reference to the current state (treat as immutable).
 * - `dispatch(action)` applies the reducer and notifies subscribers.
 * - `subscribe(fn)` registers a listener; returns an unsubscribe function.
 */
export class WidgetStore {
  #state: WidgetState;
  #subscribers: Set<Subscriber> = new Set();
  #reducer: (state: WidgetState, action: Action) => WidgetState;

  constructor(
    reducer: (state: WidgetState, action: Action) => WidgetState,
    initialState: WidgetState = INITIAL_STATE,
  ) {
    this.#reducer = reducer;
    this.#state = initialState;
  }

  getState(): WidgetState {
    return this.#state;
  }

  dispatch(action: Action): void {
    const next = this.#reducer(this.#state, action);
    if (next !== this.#state) {
      this.#state = next;
      for (const fn of this.#subscribers) {
        fn(this.#state);
      }
    }
  }

  /**
   * Subscribe to state changes.
   * @returns An unsubscribe function. Call it to stop receiving updates.
   */
  subscribe(fn: Subscriber): () => void {
    this.#subscribers.add(fn);
    return () => {
      this.#subscribers.delete(fn);
    };
  }
}
