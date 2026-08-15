import { describe, it, expect } from 'vitest';
import { rootReducer } from '../../../src/state/reducers.js';
import type { WidgetState, Action } from '../../../src/state/types.js';

const INITIAL: WidgetState = {
  isPanelOpen: false,
  messages: [],
  connectionStatus: 'disconnected',
  direction: 'auto',
  appearance: 'light',
};

describe('Reducers', () => {
  describe('OPEN_PANEL / CLOSE_PANEL', () => {
    it('OPEN_PANEL sets isPanelOpen to true', () => {
      const next = rootReducer(INITIAL, { type: 'OPEN_PANEL' });
      expect(next.isPanelOpen).toBe(true);
    });

    it('OPEN_PANEL is idempotent — returns same reference when already open', () => {
      const open = { ...INITIAL, isPanelOpen: true };
      const next = rootReducer(open, { type: 'OPEN_PANEL' });
      expect(next).toBe(open);
    });

    it('CLOSE_PANEL sets isPanelOpen to false', () => {
      const open = { ...INITIAL, isPanelOpen: true };
      const next = rootReducer(open, { type: 'CLOSE_PANEL' });
      expect(next.isPanelOpen).toBe(false);
    });

    it('CLOSE_PANEL is idempotent — returns same reference when already closed', () => {
      const next = rootReducer(INITIAL, { type: 'CLOSE_PANEL' });
      expect(next).toBe(INITIAL);
    });
  });

  describe('ADD_USER_MESSAGE', () => {
    it('appends a user message to the messages array', () => {
      const next = rootReducer(INITIAL, {
        type: 'ADD_USER_MESSAGE',
        payload: { id: 'u1', text: 'Hello' },
      });
      expect(next.messages).toHaveLength(1);
      expect(next.messages[0].role).toBe('user');
      expect(next.messages[0].text).toBe('Hello');
      expect(next.messages[0].streaming).toBe(false);
    });
  });

  describe('ADD_ASSISTANT_MESSAGE / APPEND_ASSISTANT_CHUNK / DONE_ASSISTANT_MESSAGE', () => {
    it('creates a streaming assistant message, accumulates chunks, then finishes', () => {
      let state = rootReducer(INITIAL, {
        type: 'ADD_ASSISTANT_MESSAGE',
        payload: { id: 'a1' },
      });
      expect(state.messages[0].streaming).toBe(true);
      expect(state.messages[0].text).toBe('');

      state = rootReducer(state, {
        type: 'APPEND_ASSISTANT_CHUNK',
        payload: { id: 'a1', chunk: 'Hello ' },
      });
      state = rootReducer(state, {
        type: 'APPEND_ASSISTANT_CHUNK',
        payload: { id: 'a1', chunk: 'World' },
      });
      expect(state.messages[0].text).toBe('Hello World');

      state = rootReducer(state, {
        type: 'DONE_ASSISTANT_MESSAGE',
        payload: { id: 'a1' },
      });
      expect(state.messages[0].streaming).toBe(false);
      expect(state.messages[0].isError).toBe(false);
    });
  });

  describe('ERROR_ASSISTANT_MESSAGE', () => {
    it('marks the message as error and stops streaming', () => {
      let state = rootReducer(INITIAL, {
        type: 'ADD_ASSISTANT_MESSAGE',
        payload: { id: 'a1' },
      });
      state = rootReducer(state, {
        type: 'ERROR_ASSISTANT_MESSAGE',
        payload: { id: 'a1', text: 'Something went wrong' },
      });
      expect(state.messages[0].isError).toBe(true);
      expect(state.messages[0].streaming).toBe(false);
      expect(state.messages[0].text).toBe('Something went wrong');
    });
  });

  describe('SET_CONNECTION_STATUS', () => {
    it('updates connectionStatus', () => {
      const next = rootReducer(INITIAL, {
        type: 'SET_CONNECTION_STATUS',
        payload: 'connected',
      });
      expect(next.connectionStatus).toBe('connected');
    });

    it('returns same reference when status is unchanged', () => {
      const state = { ...INITIAL, connectionStatus: 'connected' as const };
      const next = rootReducer(state, {
        type: 'SET_CONNECTION_STATUS',
        payload: 'connected',
      });
      expect(next).toBe(state);
    });
  });

  describe('SET_DIRECTION', () => {
    it('updates direction', () => {
      const next = rootReducer(INITIAL, { type: 'SET_DIRECTION', payload: 'rtl' });
      expect(next.direction).toBe('rtl');
    });
  });

  describe('SET_APPEARANCE', () => {
    it('updates appearance', () => {
      const next = rootReducer(INITIAL, { type: 'SET_APPEARANCE', payload: 'dark' });
      expect(next.appearance).toBe('dark');
    });
  });

  describe('Determinism', () => {
    it('same input always produces same output', () => {
      const action: Action = { type: 'ADD_USER_MESSAGE', payload: { id: 'u1', text: 'Hi' } };
      const r1 = rootReducer(INITIAL, action);
      const r2 = rootReducer(INITIAL, action);
      expect(r1).toEqual(r2);
    });

    it('reducer never mutates the original state object', () => {
      const frozen = Object.freeze({ ...INITIAL, messages: Object.freeze([]) as [] });
      expect(() =>
        rootReducer(frozen as WidgetState, { type: 'OPEN_PANEL' }),
      ).not.toThrow();
    });
  });
});
