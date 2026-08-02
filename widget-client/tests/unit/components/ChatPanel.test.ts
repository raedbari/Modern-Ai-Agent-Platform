import { describe, it, expect, vi } from 'vitest';
import { ChatPanel } from '../../../src/components/ChatPanel.js';
import type { ResolvedConfig } from '../../../src/config/types.js';
import type { WidgetState } from '../../../src/state/types.js';

const CONFIG: ResolvedConfig = {
  agentId: 'test',
  theme: {},
  position: 'right',
  language: 'en',
  direction: 'auto',
  transport: 'mock',
  transportUrl: '',
  mockScenario: 'happy-path',
  launcherLabel: 'Open chat',
  welcomeMessage: 'Hello!',
  shadowMode: 'open',
};

const INITIAL_STATE: WidgetState = {
  isPanelOpen: true,
  messages: [],
  connectionStatus: 'connected',
  direction: 'auto',
  appearance: 'light',
  configPatch: {},
};

describe('ChatPanel component', () => {
  it('has role="dialog", aria-modal="true", and aria-labelledby="panel-title"', () => {
    const panel = new ChatPanel({ onClose: vi.fn(), onSend: vi.fn() }, CONFIG);
    expect(panel.element.getAttribute('role')).toBe('dialog');
    expect(panel.element.getAttribute('aria-modal')).toBe('true');
    expect(panel.element.getAttribute('aria-labelledby')).toBe('panel-title');
  });

  it('has part="chat-panel" attribute', () => {
    const panel = new ChatPanel({ onClose: vi.fn(), onSend: vi.fn() }, CONFIG);
    expect(panel.element.getAttribute('part')).toBe('chat-panel');
  });

  it('hides/shows panel based on isPanelOpen', () => {
    const panel = new ChatPanel({ onClose: vi.fn(), onSend: vi.fn() }, CONFIG);

    panel.update({ ...INITIAL_STATE, isPanelOpen: false });
    expect(panel.element.hidden).toBe(true);

    panel.update({ ...INITIAL_STATE, isPanelOpen: true });
    expect(panel.element.hidden).toBe(false);
  });

  it('shows GreetingScreen when messages array is empty', () => {
    const panel = new ChatPanel({ onClose: vi.fn(), onSend: vi.fn() }, CONFIG);
    panel.update(INITIAL_STATE);

    expect(panel.greetingScreen.element.hidden).toBe(false);
    expect(panel.messageList.element.hidden).toBe(true);
  });

  it('shows MessageList when messages array is non-empty', () => {
    const panel = new ChatPanel({ onClose: vi.fn(), onSend: vi.fn() }, CONFIG);
    panel.update({
      ...INITIAL_STATE,
      messages: [
        {
          id: '1',
          role: 'user',
          text: 'Hi',
          streaming: false,
          isError: false,
          timestamp: Date.now(),
        },
      ],
    });

    expect(panel.greetingScreen.element.hidden).toBe(true);
    expect(panel.messageList.element.hidden).toBe(false);
  });

  it('shows StatusBanner when offline', () => {
    const panel = new ChatPanel({ onClose: vi.fn(), onSend: vi.fn() }, CONFIG);
    panel.update({ ...INITIAL_STATE, connectionStatus: 'disconnected' });

    expect(panel.statusBanner.element.hidden).toBe(false);
  });

  it('shows LoadingIndicator when assistant message is empty and streaming', () => {
    const panel = new ChatPanel({ onClose: vi.fn(), onSend: vi.fn() }, CONFIG);
    panel.update({
      ...INITIAL_STATE,
      messages: [
        {
          id: 'a1',
          role: 'assistant',
          text: '',
          streaming: true,
          isError: false,
          timestamp: Date.now(),
        },
      ],
    });

    expect(panel.loadingIndicator.element.hidden).toBe(false);
  });
});
