import type { ResolvedConfig } from './config/types.js';
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
  destroy(): void;
  setConfig(patch: Partial<ResolvedConfig>): void;
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

  static mount(config: ResolvedConfig): WidgetRoot {
    const existing = document.querySelector(CUSTOM_ELEMENT_TAG) as WidgetRoot | null;
    if (existing) {
      existing.setConfig(config);
      return existing;
    }

    const el = document.createElement(CUSTOM_ELEMENT_TAG) as WidgetRoot;
    el.#config = config;
    document.body.appendChild(el);
    return el;
  }

  connectedCallback(): void {
    if (!this.#config) {
      this.#config = validateConfig({});
    }

    this.#shadow = this.attachShadow({ mode: this.#config.shadowMode });
    this.#store = new WidgetStore(rootReducer);
    this.#themeInjector = new ThemeInjector(this.#shadow);

    this.#directionCtrl = new DirectionController({
      mode: this.#config.direction,
      onChange: (dir) => this.#store.dispatch({ type: 'SET_DIRECTION', payload: dir }),
    });

    this.#transport = createTransport(this.#config);
    this.#transport.onStatusChange((status) => {
      this.#store.dispatch({ type: 'SET_CONNECTION_STATUS', payload: status });
      if (status === 'connected') {
        this.#backoff.reset();
      }
    });

    this.#transport.connect().catch(() => {
      this.#scheduleReconnect();
    });

    this.#render();
    this.#registerAPI();

    // Subscribe store changes
    this.#unsubStore = this.#store.subscribe((state) => this.#onStateChange(state));
  }

  disconnectedCallback(): void {
    this.#focusTrap.deactivate();
    this.#directionCtrl.disconnect();
    this.#transport.disconnect();
    this.#unsubStore?.();

    if (window.WidgetAPI && this.#isAPIOwner()) {
      delete window.WidgetAPI;
    }
  }

  open(): void {
    this.#store.dispatch({ type: 'OPEN_PANEL' });
  }

  close(): void {
    this.#store.dispatch({ type: 'CLOSE_PANEL' });
  }

  destroy(): void {
    this.disconnectedCallback();
    this.remove();
  }

  setConfig(patch: Partial<ResolvedConfig>): void {
    this.#config = { ...this.#config, ...patch };
    this.#store.dispatch({ type: 'PATCH_CONFIG', payload: patch });

    if (patch.theme) {
      this.#themeInjector.apply(patch.theme);
    }
    if (patch.direction) {
      this.#directionCtrl.setMode(patch.direction);
    }
    if (patch.launcherLabel) {
      this.#launcher.setLabel(patch.launcherLabel);
    }
    if (patch.welcomeMessage) {
      this.#chatPanel.greetingScreen.setMessage(patch.welcomeMessage);
    }
  }

  #render(): void {
    const styleEl = document.createElement('style');
    styleEl.textContent = `
      :host {
        all: initial;
        display: block;
        position: fixed;
        ${this.#config.position === 'left' ? 'inset-inline-start: 1.5rem;' : 'inset-inline-end: 1.5rem;'}
        inset-block-end: 1.5rem;
        z-index: 2147483647;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }
      .widget-container {
        display: flex;
        flex-direction: column;
        align-items: ${this.#config.position === 'left' ? 'flex-start' : 'flex-end'};
        gap: 0.75rem;
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

    this.#shadow.appendChild(styleEl);
    this.#themeInjector.apply(this.#config.theme);

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

  #togglePanel(): void {
    if (this.#store.getState().isPanelOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  #handleSend(text: string): void {
    const userMsgId = `u-${Date.now()}`;
    const assistantMsgId = `a-${Date.now()}`;

    this.#store.dispatch({
      type: 'ADD_USER_MESSAGE',
      payload: { id: userMsgId, text },
    });

    this.#store.dispatch({
      type: 'ADD_ASSISTANT_MESSAGE',
      payload: { id: assistantMsgId },
    });

    this.#transport.send(
      { text, agentId: this.#config.agentId },
      {
        onChunk: (chunk) => {
          this.#store.dispatch({
            type: 'APPEND_ASSISTANT_CHUNK',
            payload: { id: assistantMsgId, chunk },
          });
        },
        onDone: () => {
          this.#store.dispatch({
            type: 'DONE_ASSISTANT_MESSAGE',
            payload: { id: assistantMsgId },
          });
          this.#liveRegion.announce('Assistant response complete.');
        },
        onError: (err) => {
          this.#store.dispatch({
            type: 'ERROR_ASSISTANT_MESSAGE',
            payload: { id: assistantMsgId, text: err.message },
          });
          this.#liveRegion.announce(`Error: ${err.message}`);
        },
      },
    );
  }

  #onStateChange(state: ReturnType<WidgetStore['getState']>): void {
    this.#launcher.setExpanded(state.isPanelOpen);
    this.#chatPanel.update(state);

    if (state.isPanelOpen) {
      this.#focusTrap.activate(this.#chatPanel.element, () => this.close());
    } else {
      this.#focusTrap.deactivate();
    }
  }

  #scheduleReconnect(): void {
    const delay = this.#backoff.nextDelay();
    if (delay !== null) {
      setTimeout(() => {
        this.#transport.connect().catch(() => this.#scheduleReconnect());
      }, delay);
    }
  }

  #registerAPI(): void {
    const api: WidgetAPI = {
      open: () => this.open(),
      close: () => this.close(),
      destroy: () => this.destroy(),
      setConfig: (patch) => this.setConfig(patch),
    };
    window.WidgetAPI = api;
  }

  #isAPIOwner(): boolean {
    return typeof window.WidgetAPI?.destroy === 'function';
  }
}

if (!customElements.get(CUSTOM_ELEMENT_TAG)) {
  customElements.define(CUSTOM_ELEMENT_TAG, WidgetRoot);
}
