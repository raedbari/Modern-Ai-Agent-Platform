import type {
  ResolvedConfig,
  RuntimeWidgetConfig,
} from './config/types.js';
import { validateConfig } from './config/validator.js';
import { WidgetStore } from './state/store.js';
import { rootReducer } from './state/reducers.js';
import { ThemeInjector } from './theme/injector.js';
import { DirectionController } from './utils/direction.js';
import { ExponentialBackoff } from './utils/backoff.js';
import { createTransport } from './transport/factory.js';
import type { ITransport } from './transport/types.js';
import { FocusTrap } from './a11y/focus-trap.js';
import { LiveRegion } from './a11y/live-region.js';
import { Launcher } from './components/Launcher.js';
import { ChatPanel } from './components/ChatPanel.js';
import { GreetingScreen } from './components/GreetingScreen.js';
import { MessageList } from './components/MessageList.js';
import { MessageBubble } from './components/MessageBubble.js';
import { LoadingIndicator } from './components/LoadingIndicator.js';
import { StatusBanner } from './components/StatusBanner.js';
import { InputBar } from './components/InputBar.js';
import { PanelHeader } from './components/PanelHeader.js';

export interface WidgetAPI {
  open(): void;
  close(): void;
  refresh(): Promise<void>;
  destroy(): void;
}

declare global {
  interface Window {
    WidgetAPI?: WidgetAPI;
  }
}

const CUSTOM_ELEMENT_TAG = 'maap-widget';

export class WidgetRoot extends HTMLElement {
  #config!: ResolvedConfig;
  #shadow!: ShadowRoot;
  #store!: WidgetStore;
  #themeInjector!: ThemeInjector;
  #directionCtrl!: DirectionController;
  #transport!: ITransport;
  #focusTrap = new FocusTrap();
  #liveRegion = new LiveRegion();
  #backoff = new ExponentialBackoff();
  #launcher!: Launcher;
  #chatPanel!: ChatPanel;
  #unsubStore?: () => void;
  #publicAPI?: WidgetAPI;
  #reconnectTimer: number | undefined;
  #wasPanelOpen = false;
  #isRunning = false;

  static mount(config: ResolvedConfig): WidgetRoot {
    const existing = document.querySelector(CUSTOM_ELEMENT_TAG) as WidgetRoot | null;
    if (existing) return existing;

    const element = document.createElement(CUSTOM_ELEMENT_TAG) as WidgetRoot;
    element.#config = config;
    document.body.appendChild(element);
    return element;
  }

  connectedCallback(): void {
    if (this.#isRunning) return;
    this.#isRunning = true;
    if (!this.#config) this.#config = validateConfig({});

    this.#shadow = this.attachShadow({ mode: this.#config.shadowMode });
    this.#store = new WidgetStore(rootReducer);
    this.#themeInjector = new ThemeInjector(this.#shadow);
    this.#transport = createTransport(this.#config);

    this.#directionCtrl = new DirectionController({
      mode: this.#config.direction,
      onChange: (direction) => {
        this.#store.dispatch({ type: 'SET_DIRECTION', payload: direction });
      },
    });

    this.#transport.onStatusChange((status) => {
      this.#store.dispatch({ type: 'SET_CONNECTION_STATUS', payload: status });
      if (status === 'connected') this.#backoff.reset();
    });

    this.#render();
    this.#registerAPI();
    this.#unsubStore = this.#store.subscribe((state) => this.#onStateChange(state));
    this.#store.dispatch({
      type: 'SET_DIRECTION',
      payload: this.#directionCtrl.direction,
    });
    this.#store.dispatch({
      type: 'SET_APPEARANCE',
      payload: this.#config.appearance,
    });
    this.#onStateChange(this.#store.getState());
    void this.#connectTransport();
  }

  disconnectedCallback(): void {
    if (!this.#isRunning) return;
    this.#isRunning = false;
    if (this.#reconnectTimer !== undefined) {
      window.clearTimeout(this.#reconnectTimer);
      this.#reconnectTimer = undefined;
    }
    this.#focusTrap.deactivate();
    this.#directionCtrl.disconnect();
    this.#transport.disconnect();
    this.#unsubStore?.();
    this.#unsubStore = undefined;
    if (window.WidgetAPI === this.#publicAPI) delete window.WidgetAPI;
    this.#publicAPI = undefined;
  }

  open(): void {
    this.#store.dispatch({ type: 'OPEN_PANEL' });
  }

  close(): void {
    this.#store.dispatch({ type: 'CLOSE_PANEL' });
  }

  async refresh(): Promise<void> {
    await this.#connectTransport();
  }

  destroy(): void {
    this.remove();
  }

  #render(): void {
    this.setAttribute('data-position', this.#config.position);
    this.setAttribute('data-appearance', this.#config.appearance);
    this.lang = this.#config.language;

    const styleElement = document.createElement('style');
    styleElement.textContent = `
      :host {
        all: initial;
        position: fixed;
        inset-inline-end: 1.25rem;
        inset-block-end: max(1.25rem, env(safe-area-inset-bottom));
        display: block;
        z-index: 2147483647;
        direction: ltr;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system,
          BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-synthesis: none;
        text-rendering: optimizeLegibility;
      }
      :host([dir='rtl']) { direction: rtl; }
      :host([data-position='left']) {
        inset-inline-start: 1.25rem;
        inset-inline-end: auto;
      }
      *, *::before, *::after {
        box-sizing: border-box;
      }
      [hidden] {
        display: none !important;
      }
      .widget-container {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        gap: 0.8rem;
      }
      :host([data-position='left']) .widget-container { align-items: flex-start; }
      @media (max-width: 30rem) {
        :host {
          inset-inline-end: 0.5rem;
          inset-block-end: max(0.5rem, env(safe-area-inset-bottom));
        }
        :host([data-position='left']) {
          inset-inline-start: 0.5rem;
          inset-inline-end: auto;
        }
      }
      ${Launcher.styles()}
      ${PanelHeader.styles()}
      ${StatusBanner.styles()}
      ${GreetingScreen.styles()}
      ${MessageList.styles()}
      ${MessageBubble.styles()}
      ${LoadingIndicator.styles()}
      ${InputBar.styles()}
      ${ChatPanel.styles()}
    `;
    this.#shadow.appendChild(styleElement);
    this.#themeInjector.apply(this.#config.theme, this.#config.appearance);

    const container = document.createElement('div');
    container.className = 'widget-container';
    this.#launcher = new Launcher(
      { onClick: () => this.#togglePanel() },
      this.#config.launcherLabel,
    );
    this.#chatPanel = new ChatPanel(
      {
        onClose: () => this.close(),
        onSend: (text) => this.#handleSend(text),
      },
      this.#config,
    );
    container.appendChild(this.#chatPanel.element);
    container.appendChild(this.#launcher.element);
    container.appendChild(this.#liveRegion.element);
    this.#shadow.appendChild(container);
  }

  async #connectTransport(): Promise<void> {
    try {
      const runtimeConfig = await this.#transport.connect();
      if (runtimeConfig && this.#isRunning) {
        this.#applyRuntimeConfig(runtimeConfig);
      }
    } catch (error) {
      if (!isNonRetryableTransportError(error)) this.#scheduleReconnect();
    }
  }

  #applyRuntimeConfig(runtimeConfig: RuntimeWidgetConfig): void {
    this.#config = { ...this.#config, ...runtimeConfig };
    this.setAttribute('data-position', runtimeConfig.position);
    this.setAttribute('data-appearance', runtimeConfig.appearance);
    this.#themeInjector.apply(runtimeConfig.theme, runtimeConfig.appearance);
    this.#chatPanel.setRuntimePresentation(
      runtimeConfig.displayName,
      runtimeConfig.welcomeMessage,
    );
    this.#store.dispatch({
      type: 'SET_APPEARANCE',
      payload: runtimeConfig.appearance,
    });
  }

  #togglePanel(): void {
    if (this.#store.getState().isPanelOpen) this.close();
    else this.open();
  }

  #handleSend(text: string): void {
    const requestId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const userMessageId = `u-${requestId}`;
    const assistantMessageId = `a-${requestId}`;

    this.#store.dispatch({
      type: 'ADD_USER_MESSAGE',
      payload: { id: userMessageId, text },
    });
    this.#store.dispatch({
      type: 'ADD_ASSISTANT_MESSAGE',
      payload: { id: assistantMessageId },
    });

    this.#transport.send(
      { text },
      {
        onChunk: (chunk) => {
          this.#store.dispatch({
            type: 'APPEND_ASSISTANT_CHUNK',
            payload: { id: assistantMessageId, chunk },
          });
        },
        onDone: () => {
          this.#store.dispatch({
            type: 'DONE_ASSISTANT_MESSAGE',
            payload: { id: assistantMessageId },
          });
          this.#liveRegion.announce('Assistant response complete.');
        },
        onError: (error) => {
          this.#store.dispatch({
            type: 'ERROR_ASSISTANT_MESSAGE',
            payload: { id: assistantMessageId, text: error.message },
          });
          this.#liveRegion.announce(error.message);
        },
      },
    );
  }

  #onStateChange(state: ReturnType<WidgetStore['getState']>): void {
    this.dir = state.direction === 'rtl' ? 'rtl' : 'ltr';
    this.#launcher.setExpanded(state.isPanelOpen);
    this.#launcher.setConnectionStatus(state.connectionStatus);
    this.#chatPanel.update(state);

    if (state.isPanelOpen && !this.#wasPanelOpen) {
      this.#focusTrap.activate(this.#chatPanel.element, () => this.close());
    } else if (!state.isPanelOpen && this.#wasPanelOpen) {
      this.#focusTrap.deactivate();
    }
    this.#wasPanelOpen = state.isPanelOpen;
  }

  #scheduleReconnect(): void {
    if (!this.#isRunning || this.#reconnectTimer !== undefined) return;
    const delay = this.#backoff.nextDelay();
    if (delay === null) return;
    this.#reconnectTimer = window.setTimeout(() => {
      this.#reconnectTimer = undefined;
      void this.#connectTransport();
    }, delay);
  }

  #registerAPI(): void {
    this.#publicAPI = {
      open: () => this.open(),
      close: () => this.close(),
      refresh: () => this.refresh(),
      destroy: () => this.destroy(),
    };
    window.WidgetAPI = this.#publicAPI;
  }
}

function isNonRetryableTransportError(error: unknown): boolean {
  if (typeof error !== 'object' || error === null) return false;
  return 'retryable' in error && error.retryable === false;
}

if (!customElements.get(CUSTOM_ELEMENT_TAG)) {
  customElements.define(CUSTOM_ELEMENT_TAG, WidgetRoot);
}
