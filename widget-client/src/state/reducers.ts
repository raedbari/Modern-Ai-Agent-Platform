import type { WidgetState, Action, Message } from './types.js';

/** Pure root reducer — never mutates state, always returns a new object. */
export function rootReducer(state: WidgetState, action: Action): WidgetState {
  switch (action.type) {
    case 'OPEN_PANEL':
      if (state.isPanelOpen) return state;
      return { ...state, isPanelOpen: true };

    case 'CLOSE_PANEL':
      if (!state.isPanelOpen) return state;
      return { ...state, isPanelOpen: false };

    case 'ADD_USER_MESSAGE': {
      const { id, text } = action.payload;
      const msg: Message = {
        id,
        role: 'user',
        text,
        streaming: false,
        isError: false,
        timestamp: Date.now(),
      };
      return { ...state, messages: [...state.messages, msg] };
    }

    case 'ADD_ASSISTANT_MESSAGE': {
      const { id } = action.payload;
      const msg: Message = {
        id,
        role: 'assistant',
        text: '',
        streaming: true,
        isError: false,
        timestamp: Date.now(),
      };
      return { ...state, messages: [...state.messages, msg] };
    }

    case 'APPEND_ASSISTANT_CHUNK': {
      const { id, chunk } = action.payload;
      return {
        ...state,
        messages: state.messages.map((m) =>
          m.id === id ? { ...m, text: m.text + chunk } : m,
        ),
      };
    }

    case 'DONE_ASSISTANT_MESSAGE': {
      const { id } = action.payload;
      return {
        ...state,
        messages: state.messages.map((m) =>
          m.id === id ? { ...m, streaming: false } : m,
        ),
      };
    }

    case 'ERROR_ASSISTANT_MESSAGE': {
      const { id, text } = action.payload;
      return {
        ...state,
        messages: state.messages.map((m) =>
          m.id === id ? { ...m, text, streaming: false, isError: true } : m,
        ),
      };
    }

    case 'SET_CONNECTION_STATUS':
      if (state.connectionStatus === action.payload) return state;
      return { ...state, connectionStatus: action.payload };

    case 'SET_DIRECTION':
      if (state.direction === action.payload) return state;
      return { ...state, direction: action.payload };

    case 'SET_APPEARANCE':
      if (state.appearance === action.payload) return state;
      return { ...state, appearance: action.payload };

    default: {
      // Exhaustiveness guard
      const _exhaustive: never = action;
      return _exhaustive;
    }
  }
}
