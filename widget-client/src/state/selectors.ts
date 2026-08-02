import type { WidgetState } from './types.js';

/**
 * showGreeting — true when no messages have been exchanged yet.
 * Used to decide whether to show the GreetingScreen or MessageList.
 */
export function showGreeting(state: WidgetState): boolean {
  return state.messages.length === 0;
}

/**
 * isOffline — true when the connection status indicates no connectivity.
 */
export function isOffline(state: WidgetState): boolean {
  return state.connectionStatus === 'disconnected' || state.connectionStatus === 'error';
}

/**
 * sendDisabled — true when the user should not be allowed to submit a new message.
 * Currently: disabled while an assistant message is still streaming.
 */
export function sendDisabled(state: WidgetState): boolean {
  return (
    state.connectionStatus !== 'connected'
    || state.messages.some((m) => m.role === 'assistant' && m.streaming)
  );
}

/**
 * inputEditable — always true per spec.
 * The textarea is never disabled; only the send button reflects sendDisabled.
 */
export function inputEditable(state: WidgetState): boolean {
  void state;
  return true;
}
