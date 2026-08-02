import type { ConnectionStatus } from '../transport/types.js';

// ─── Domain types ─────────────────────────────────────────────────────────────

export type MessageRole = 'user' | 'assistant';
export type Appearance = 'light' | 'dark';
export type Direction = 'ltr' | 'rtl' | 'auto';

export interface Message {
  id: string;
  role: MessageRole;
  /** For assistant messages this accumulates streamed chunks. */
  text: string;
  /** True while the assistant is still streaming. */
  streaming: boolean;
  /** True if the message ended with an error. */
  isError: boolean;
  timestamp: number;
}

// ─── Widget state ─────────────────────────────────────────────────────────────

export interface WidgetState {
  isPanelOpen: boolean;
  messages: Message[];
  connectionStatus: ConnectionStatus;
  direction: Direction;
  appearance: Appearance;
  /** Partial config patches applied at runtime via setConfig(). */
  configPatch: Record<string, unknown>;
}

// ─── Action union ─────────────────────────────────────────────────────────────

export type Action =
  | { type: 'OPEN_PANEL' }
  | { type: 'CLOSE_PANEL' }
  | { type: 'ADD_USER_MESSAGE'; payload: { id: string; text: string } }
  | { type: 'ADD_ASSISTANT_MESSAGE'; payload: { id: string } }
  | { type: 'APPEND_ASSISTANT_CHUNK'; payload: { id: string; chunk: string } }
  | { type: 'DONE_ASSISTANT_MESSAGE'; payload: { id: string } }
  | { type: 'ERROR_ASSISTANT_MESSAGE'; payload: { id: string; text: string } }
  | { type: 'SET_CONNECTION_STATUS'; payload: ConnectionStatus }
  | { type: 'SET_DIRECTION'; payload: Direction }
  | { type: 'SET_APPEARANCE'; payload: Appearance }
  | { type: 'PATCH_CONFIG'; payload: Record<string, unknown> };
