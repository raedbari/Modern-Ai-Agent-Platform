import { describe, it, expect } from 'vitest';
import {
  showGreeting,
  isOffline,
  sendDisabled,
  inputEditable,
} from '../../../src/state/selectors.js';
import type { WidgetState, Message } from '../../../src/state/types.js';

function makeState(overrides: Partial<WidgetState> = {}): WidgetState {
  return {
    isPanelOpen: false,
    messages: [],
    connectionStatus: 'connected',
    direction: 'auto',
    appearance: 'light',
    ...overrides,
  };
}

function makeMsg(overrides: Partial<Message>): Message {
  return {
    id: 'msg-1',
    role: 'assistant',
    text: 'Hi',
    streaming: false,
    isError: false,
    timestamp: Date.now(),
    ...overrides,
  };
}

describe('showGreeting', () => {
  it('returns true when there are no messages', () => {
    expect(showGreeting(makeState())).toBe(true);
  });

  it('returns false when at least one message exists', () => {
    expect(showGreeting(makeState({ messages: [makeMsg({ role: 'user' })] }))).toBe(false);
  });
});

describe('isOffline', () => {
  it('returns false when connected', () => {
    expect(isOffline(makeState({ connectionStatus: 'connected' }))).toBe(false);
  });

  it('returns true when disconnected', () => {
    expect(isOffline(makeState({ connectionStatus: 'disconnected' }))).toBe(true);
  });

  it('returns true when status is error', () => {
    expect(isOffline(makeState({ connectionStatus: 'error' }))).toBe(true);
  });

  it('returns false when connecting', () => {
    expect(isOffline(makeState({ connectionStatus: 'connecting' }))).toBe(false);
  });
});

describe('sendDisabled', () => {
  it('returns false when no messages', () => {
    expect(sendDisabled(makeState())).toBe(false);
  });

  it('returns true when an assistant message is streaming', () => {
    const state = makeState({
      messages: [makeMsg({ role: 'assistant', streaming: true })],
    });
    expect(sendDisabled(state)).toBe(true);
  });

  it('returns false when all messages have finished streaming', () => {
    const state = makeState({
      messages: [makeMsg({ role: 'assistant', streaming: false })],
    });
    expect(sendDisabled(state)).toBe(false);
  });

  it('returns true even if only one out of multiple messages is streaming', () => {
    const state = makeState({
      messages: [
        makeMsg({ id: 'a1', role: 'assistant', streaming: false }),
        makeMsg({ id: 'a2', role: 'assistant', streaming: true }),
      ],
    });
    expect(sendDisabled(state)).toBe(true);
  });
});

describe('inputEditable', () => {
  it('always returns true regardless of state', () => {
    expect(inputEditable(makeState())).toBe(true);
    expect(inputEditable(makeState({ connectionStatus: 'error' }))).toBe(true);
    expect(
      inputEditable(makeState({ messages: [makeMsg({ streaming: true })] })),
    ).toBe(true);
  });
});
