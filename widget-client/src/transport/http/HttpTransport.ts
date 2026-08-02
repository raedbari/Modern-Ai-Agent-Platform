import type {
  ITransport,
  ConnectionStatus,
  MessageCallbacks,
  OutgoingMessage,
  TransportError,
} from '../types.js';
import type {
  RuntimeWidgetConfig,
  ThemeTokens,
  WidgetAppearance,
  WidgetPosition,
} from '../../config/types.js';

interface HttpTransportOptions {
  apiBaseUrl: string;
  widgetId: string;
}

interface BootstrapPayload {
  session_token: string;
  token_type: 'Bearer';
  expires_in: number;
  session_id: string;
  widget: {
    widget_id: string;
    display_name: string;
    greeting: string | null;
    theme: {
      primaryColor: string;
      textColor: string;
      launcherColor: string;
      headerColor: string;
      userMessageColor: string;
      position: WidgetPosition;
      appearance: WidgetAppearance;
    };
  };
}

interface ChatPayload {
  conversation_id: string;
  reply: string;
}

type StatusListener = (status: ConnectionStatus) => void;

const TOKEN_REFRESH_SKEW_MS = 15_000;
const HEX_COLOR = /^#[0-9A-Fa-f]{6}$/;

/**
 * Production transport for the existing FastAPI Widget contract.
 *
 * The short-lived JWT and conversation identifier remain in memory only.
 * Agent and tenant identity are derived exclusively from the signed token.
 */
export class HttpTransport implements ITransport {
  readonly #apiBaseUrl: string;
  readonly #widgetId: string;
  #status: ConnectionStatus = 'disconnected';
  #statusListeners: StatusListener[] = [];
  #sessionToken = '';
  #sessionExpiresAt = 0;
  #conversationId: string | undefined;
  #connectPromise: Promise<RuntimeWidgetConfig> | null = null;
  #bootstrapController: AbortController | null = null;
  #activeController: AbortController | null = null;

  constructor(options: HttpTransportOptions) {
    this.#apiBaseUrl = options.apiBaseUrl;
    this.#widgetId = options.widgetId;
  }

  async connect(): Promise<RuntimeWidgetConfig> {
    if (this.#connectPromise) return this.#connectPromise;
    this.#connectPromise = this.#bootstrap();
    try {
      return await this.#connectPromise;
    } finally {
      this.#connectPromise = null;
    }
  }

  send(message: OutgoingMessage, callbacks: MessageCallbacks): () => void {
    this.#activeController?.abort();
    const controller = new AbortController();
    this.#activeController = controller;

    void this.#sendMessage(message, callbacks, controller, true).finally(() => {
      if (this.#activeController === controller) {
        this.#activeController = null;
      }
    });

    return () => controller.abort();
  }

  disconnect(): void {
    this.#bootstrapController?.abort();
    this.#bootstrapController = null;
    this.#activeController?.abort();
    this.#activeController = null;
    this.#sessionToken = '';
    this.#sessionExpiresAt = 0;
    this.#conversationId = undefined;
    this.#setStatus('disconnected');
  }

  onStatusChange(listener: StatusListener): void {
    this.#statusListeners.push(listener);
  }

  async #bootstrap(): Promise<RuntimeWidgetConfig> {
    this.#setStatus('connecting');
    if (!this.#apiBaseUrl || !this.#widgetId) {
      this.#setStatus('error');
      throw {
        code: 'invalid_config',
        message: 'Live Widget configuration is incomplete.',
        retryable: false,
      } satisfies TransportError;
    }

    const controller = new AbortController();
    this.#bootstrapController?.abort();
    this.#bootstrapController = controller;
    try {
      const response = await fetch(`${this.#apiBaseUrl}/api/widget/bootstrap`, {
        method: 'POST',
        mode: 'cors',
        credentials: 'omit',
        cache: 'no-store',
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ widget_id: this.#widgetId }),
      });

      if (!response.ok) {
        throw await responseError(response, 'bootstrap_failed');
      }

      const payload = validateBootstrapPayload(await response.json(), this.#widgetId);
      if (controller.signal.aborted) {
        throw new DOMException('Widget bootstrap aborted.', 'AbortError');
      }
      this.#sessionToken = payload.session_token;
      this.#sessionExpiresAt = Date.now() + payload.expires_in * 1_000;
      this.#conversationId = undefined;
      this.#setStatus('connected');
      return toRuntimeConfig(payload);
    } catch (error) {
      this.#setStatus(controller.signal.aborted ? 'disconnected' : 'error');
      throw error;
    } finally {
      if (this.#bootstrapController === controller) {
        this.#bootstrapController = null;
      }
    }
  }

  async #sendMessage(
    message: OutgoingMessage,
    callbacks: MessageCallbacks,
    controller: AbortController,
    allowSessionRetry: boolean,
  ): Promise<void> {
    try {
      if (
        !this.#sessionToken
        || this.#sessionExpiresAt <= Date.now() + TOKEN_REFRESH_SKEW_MS
      ) {
        await this.connect();
      }

      const body: { message: string; conversation_id: string | null } = {
        message: message.text,
        conversation_id: this.#conversationId ?? null,
      };

      const response = await fetch(`${this.#apiBaseUrl}/api/chat`, {
        method: 'POST',
        mode: 'cors',
        credentials: 'omit',
        cache: 'no-store',
        signal: controller.signal,
        headers: {
          Authorization: `Bearer ${this.#sessionToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (response.status === 401 && allowSessionRetry) {
        this.#sessionToken = '';
        this.#sessionExpiresAt = 0;
        await this.connect();
        await this.#sendMessage(message, callbacks, controller, false);
        return;
      }
      if (!response.ok) {
        throw await responseError(response, 'chat_failed');
      }

      const payload = validateChatPayload(await response.json());
      this.#conversationId = payload.conversation_id;
      this.#setStatus('connected');
      callbacks.onChunk(payload.reply);
      callbacks.onDone();
    } catch (error) {
      if (controller.signal.aborted) return;
      const transportError = toTransportError(error);
      if (
        transportError.code === 'network_error'
        || transportError.code === 'chat_failed'
      ) {
        this.#setStatus('error');
      }
      callbacks.onError(transportError);
    }
  }

  #setStatus(status: ConnectionStatus): void {
    if (status === this.#status) return;
    this.#status = status;
    for (const listener of this.#statusListeners) listener(status);
  }
}

function validateBootstrapPayload(
  value: unknown,
  expectedWidgetId: string,
): BootstrapPayload {
  if (!isRecord(value) || !isRecord(value.widget) || !isRecord(value.widget.theme)) {
    throw new Error('Invalid Widget bootstrap response.');
  }
  const theme = value.widget.theme;
  const colours = [
    theme.primaryColor,
    theme.textColor,
    theme.launcherColor,
    theme.headerColor,
    theme.userMessageColor,
  ];
  if (
    typeof value.session_token !== 'string'
    || !value.session_token
    || value.token_type !== 'Bearer'
    || typeof value.expires_in !== 'number'
    || !Number.isFinite(value.expires_in)
    || value.expires_in <= 0
    || typeof value.session_id !== 'string'
    || !value.session_id
    || value.widget.widget_id !== expectedWidgetId
    || typeof value.widget.display_name !== 'string'
    || !value.widget.display_name.trim()
    || (value.widget.greeting !== null && typeof value.widget.greeting !== 'string')
    || !colours.every((colour) => typeof colour === 'string' && HEX_COLOR.test(colour))
    || (theme.position !== 'left' && theme.position !== 'right')
    || (theme.appearance !== 'light' && theme.appearance !== 'dark')
  ) {
    throw new Error('Invalid Widget bootstrap response.');
  }
  return value as unknown as BootstrapPayload;
}

function validateChatPayload(value: unknown): ChatPayload {
  if (
    !isRecord(value)
    || typeof value.conversation_id !== 'string'
    || !value.conversation_id
    || typeof value.reply !== 'string'
    || !value.reply
  ) {
    throw new Error('Invalid chat response.');
  }
  return value as unknown as ChatPayload;
}

function toRuntimeConfig(payload: BootstrapPayload): RuntimeWidgetConfig {
  const theme = payload.widget.theme;
  const tokens: ThemeTokens = {
    primary: theme.primaryColor,
    onPrimary: theme.textColor,
    launcherBg: theme.launcherColor,
    headerBg: theme.headerColor,
    userBubbleBg: theme.userMessageColor,
  };
  return {
    displayName: payload.widget.display_name,
    welcomeMessage: payload.widget.greeting ?? '',
    theme: tokens,
    position: theme.position,
    appearance: theme.appearance,
  };
}

async function responseError(
  response: Response,
  fallbackCode: string,
): Promise<TransportError> {
  const status = response.status;
  if (status === 429) {
    return {
      code: 'rate_limited',
      message: 'Too many requests. Please wait a moment and try again.',
      retryable: true,
    };
  }
  if (status === 401) {
    return {
      code: 'session_expired',
      message: 'Your chat session expired. Please try again.',
      retryable: true,
    };
  }
  if (status === 403 || status === 404) {
    return {
      code: 'widget_unavailable',
      message: 'This chat is not available on this website.',
      retryable: false,
    };
  }
  if (status === 400 || status === 422) {
    return {
      code: 'invalid_request',
      message: 'Please check your message and try again.',
      retryable: false,
    };
  }
  return {
    code: fallbackCode,
    message: 'Chat is temporarily unavailable. Please try again shortly.',
    retryable: status >= 500,
  };
}

function toTransportError(error: unknown): TransportError {
  if (isTransportError(error)) return error;
  return {
    code: 'network_error',
    message: 'Chat is temporarily unavailable. Please check your connection.',
    retryable: true,
  };
}

function isTransportError(value: unknown): value is TransportError {
  return (
    isRecord(value)
    && typeof value.code === 'string'
    && typeof value.message === 'string'
    && typeof value.retryable === 'boolean'
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}
