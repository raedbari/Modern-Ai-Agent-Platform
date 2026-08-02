import type {
  ResolvedConfig,
  RuntimeWidgetConfig,
  WidgetConfig,
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
import widgetStyles from './styles/widget.css?inline';

export interface WidgetAPI {
  open(): void;
  close(): void;
  setConfig(config: Partial<WidgetConfig>): Promise<void>;
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

    this.#directionCtrl = this.#createDirectionController(
      this.#config.direction,
    );

    this.#listenToTransport(this.#transport);

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

  /** Apply safe embed settings without allowing production theme spoofing. */
  async setConfig(patch: Partial<WidgetConfig>): Promise<void> {
    const current = this.#config;
    const currentMock = current.transport === 'mock'
      ? {
          displayName: current.displayName,
          welcomeMessage: current.welcomeMessage,
          theme: current.theme,
          position: current.position,
          appearance: current.appearance,
        }
      : undefined;
    const mergedMock = patch.mock
      ? {
          ...currentMock,
          ...patch.mock,
          theme: {
            ...currentMock?.theme,
            ...patch.mock.theme,
          },
        }
      : currentMock;
    const next = validateConfig({
      widgetId: current.widgetId,
      apiBaseUrl: current.apiBaseUrl,
      transport: current.transport,
      mockScenario: current.mockScenario,
      language: current.language,
      direction: current.direction,
      position: current.positionOverride,
      launcherLabel: current.launcherLabel,
      shadowMode: current.shadowMode,
      ...patch,
      mock: mergedMock,
    });

    if (next.shadowMode !== current.shadowMode) {
      console.warn(
        '[WidgetClient] shadowMode cannot change after mount; keeping the active mode.',
      );
      next.shadowMode = current.shadowMode;
    }

    const transportChanged = next.transport !== current.transport
      || next.widgetId !== current.widgetId
      || next.apiBaseUrl !== current.apiBaseUrl
      || next.mockScenario !== current.mockScenario;
    const directionChanged = next.direction !== current.direction;
    const identityChanged = next.widgetId !== current.widgetId
      || next.apiBaseUrl !== current.apiBaseUrl
      || next.transport !== current.transport;

    if (next.transport === 'http' && !identityChanged) {
      next.displayName = current.displayName;
      next.welcomeMessage = current.welcomeMessage;
      next.theme = current.theme;
      next.appearance = current.appearance;
      next.position = next.positionOverride ?? current.position;
    }

    this.#config = next;
    this.lang = next.language;
    this.setAttribute('data-position', next.position);
    this.setAttribute('data-appearance', next.appearance);
    this.#launcher.setLabel(next.launcherLabel);
    this.#themeInjector.apply(next.theme, next.appearance);
    this.#chatPanel.setRuntimePresentation(
      next.displayName,
      next.welcomeMessage,
    );
    this.#store.dispatch({ type: 'SET_APPEARANCE', payload: next.appearance });

    if (directionChanged) {
      this.#directionCtrl.disconnect();
      this.#directionCtrl = this.#createDirectionController(next.direction);
      this.#store.dispatch({
        type: 'SET_DIRECTION',
        payload: this.#directionCtrl.direction,
      });
    }

    if (transportChanged) {
      this.#transport.disconnect();
      this.#transport = createTransport(next);
      this.#listenToTransport(this.#transport);
      await this.#connectTransport();
    }
  }

  destroy(): void {
    this.remove();
  }

  #render(): void {
    this.setAttribute('data-position', this.#config.position);
    this.setAttribute('data-appearance', this.#config.appearance);
    this.lang = this.#config.language;

    const styleElement = document.createElement('style');
    styleElement.textContent = widgetStyles;
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
    const position = this.#config.positionOverride ?? runtimeConfig.position;
    this.#config = { ...this.#config, ...runtimeConfig, position };
    this.setAttribute('data-position', position);
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
      this.#launcher.element.focus();
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
      setConfig: (config) => this.setConfig(config),
      refresh: () => this.refresh(),
      destroy: () => this.destroy(),
    };
    window.WidgetAPI = this.#publicAPI;
  }

  #listenToTransport(transport: ITransport): void {
    transport.onStatusChange((status) => {
      if (transport !== this.#transport) return;
      this.#store.dispatch({ type: 'SET_CONNECTION_STATUS', payload: status });
      if (status === 'connected') this.#backoff.reset();
    });
  }

  #createDirectionController(
    mode: ResolvedConfig['direction'],
  ): DirectionController {
    return new DirectionController({
      mode,
      onChange: (direction) => {
        this.#store.dispatch({ type: 'SET_DIRECTION', payload: direction });
      },
    });
  }
}

function isNonRetryableTransportError(error: unknown): boolean {
  if (typeof error !== 'object' || error === null) return false;
  return 'retryable' in error && error.retryable === false;
}

if (!customElements.get(CUSTOM_ELEMENT_TAG)) {
  customElements.define(CUSTOM_ELEMENT_TAG, WidgetRoot);
}
