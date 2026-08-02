import type { WidgetState } from '../state/types.js';
import type { ResolvedConfig } from '../config/types.js';
import { PanelHeader } from './PanelHeader.js';
import { StatusBanner } from './StatusBanner.js';
import { GreetingScreen } from './GreetingScreen.js';
import { MessageList } from './MessageList.js';
import { LoadingIndicator } from './LoadingIndicator.js';
import { InputBar } from './InputBar.js';
import { showGreeting, isOffline, sendDisabled } from '../state/selectors.js';

export interface ChatPanelCallbacks {
  onClose(): void;
  onSend(text: string): void;
}

/**
 * ChatPanel — the main chat window dialog.
 *
 * Requirements:
 *  - role="dialog", aria-modal="true", aria-labelledby="panel-title"
 *  - part="chat-panel" for host CSS overrides
 *  - Composes PanelHeader + StatusBanner + GreetingScreen / MessageList + LoadingIndicator + InputBar
 *  - Manages open/close visibility
 */
export class ChatPanel {
  readonly #root: HTMLElement;
  readonly #header: PanelHeader;
  readonly #statusBanner: StatusBanner;
  readonly #greetingScreen: GreetingScreen;
  readonly #messageList: MessageList;
  readonly #loadingIndicator: LoadingIndicator;
  readonly #inputBar: InputBar;
  readonly #callbacks: ChatPanelCallbacks;

  constructor(callbacks: ChatPanelCallbacks, config: ResolvedConfig) {
    this.#callbacks = callbacks;

    this.#root = document.createElement('section');
    this.#root.className = 'chat-panel';
    this.#root.setAttribute('role', 'dialog');
    this.#root.setAttribute('aria-modal', 'true');
    this.#root.setAttribute('aria-labelledby', 'panel-title');
    this.#root.setAttribute('part', 'chat-panel');
    this.#root.hidden = true;

    // Sub-components
    this.#header = new PanelHeader({ onClose: () => this.#callbacks.onClose() });
    this.#statusBanner = new StatusBanner();
    this.#greetingScreen = new GreetingScreen(config.welcomeMessage);
    this.#messageList = new MessageList();
    this.#loadingIndicator = new LoadingIndicator();
    this.#inputBar = new InputBar({ onSend: (text) => this.#callbacks.onSend(text) });

    // Assemble structure
    this.#root.appendChild(this.#header.element);
    this.#root.appendChild(this.#statusBanner.element);

    const body = document.createElement('div');
    body.className = 'chat-panel__body';
    body.appendChild(this.#greetingScreen.element);
    body.appendChild(this.#messageList.element);
    body.appendChild(this.#loadingIndicator.element);

    this.#root.appendChild(body);
    this.#root.appendChild(this.#inputBar.element);

    // Initial visibility state
    this.#messageList.element.hidden = true;
  }

  get element(): HTMLElement {
    return this.#root;
  }

  get header(): PanelHeader {
    return this.#header;
  }

  get statusBanner(): StatusBanner {
    return this.#statusBanner;
  }

  get greetingScreen(): GreetingScreen {
    return this.#greetingScreen;
  }

  get messageList(): MessageList {
    return this.#messageList;
  }

  get loadingIndicator(): LoadingIndicator {
    return this.#loadingIndicator;
  }

  get inputBar(): InputBar {
    return this.#inputBar;
  }

  /** Sync ChatPanel rendering to state */
  update(state: WidgetState): void {
    this.#root.hidden = !state.isPanelOpen;

    // Greeting screen vs Message list
    const greeting = showGreeting(state);
    this.#greetingScreen.element.hidden = !greeting;
    this.#messageList.element.hidden = greeting;

    if (!greeting) {
      this.#messageList.update(state.messages);
    }

    // Connection / Error banner
    if (isOffline(state)) {
      this.#statusBanner.show('offline');
    } else {
      this.#statusBanner.hide();
    }

    // Typing indicator
    const streaming = state.messages.some((m) => m.role === 'assistant' && m.streaming && !m.text);
    if (streaming) {
      this.#loadingIndicator.show();
    } else {
      this.#loadingIndicator.hide();
    }

    // Input bar send button
    this.#inputBar.setSendDisabled(sendDisabled(state));
  }

  static styles(): string {
    return `
      .chat-panel {
        display: flex;
        flex-direction: column;
        inline-size: 24rem;
        max-inline-size: calc(100vw - 2rem);
        block-size: 34rem;
        max-block-size: calc(100vh - 5rem);
        background: #ffffff;
        border-radius: 1rem;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        overflow: hidden;
      }
      .chat-panel[hidden] {
        display: none !important;
      }
      .chat-panel__body {
        flex: 1;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        position: relative;
      }
    `;
  }
}
