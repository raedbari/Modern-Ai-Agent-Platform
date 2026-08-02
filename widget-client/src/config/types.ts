/**
 * Raw configuration passed by the host page via window.WidgetConfig
 * or the data-widget-config attribute. All fields except agentId are optional.
 */
export interface WidgetConfig {
  /** Identifier of the agent to connect to. Strongly recommended. */
  agentId?: string;

  /** Theme colour overrides. Keys map to CSS Custom Property tokens. */
  theme?: Partial<ThemeTokens>;

  /** Which corner the launcher occupies. Defaults to "right". */
  position?: 'left' | 'right';

  /** BCP-47 language tag, e.g. "en", "ar". */
  language?: string;

  /** Explicit text direction. Auto-detected when omitted. */
  direction?: 'ltr' | 'rtl';

  /** Transport mechanism. Defaults to "mock". */
  transport?: 'mock' | 'websocket' | 'sse';

  /** URL for the real transport (required for websocket / sse). */
  transportUrl?: string;

  /** Mock scenario to use when transport is "mock". Defaults to "happy-path". */
  mockScenario?: 'happy-path' | 'slow-response' | 'error-response' | 'stream-error-midway';

  /** Accessible label on the launcher button. */
  launcherLabel?: string;

  /** Greeting message shown before the first user message. */
  welcomeMessage?: string;

  /** Shadow DOM encapsulation mode. Defaults to "open". */
  shadowMode?: 'open' | 'closed';
}

/** Colour token keys configurable by the host page. */
export interface ThemeTokens {
  primary: string;
  text: string;
  launcherBg: string;
  headerBg: string;
  userBubbleBg: string;
}

/**
 * Resolved configuration — all optional fields have been filled with defaults.
 * The rest of the widget always works with this type.
 */
export interface ResolvedConfig {
  agentId: string;
  theme: Partial<ThemeTokens>;
  position: 'left' | 'right';
  language: string;
  direction: 'ltr' | 'rtl' | 'auto';
  transport: 'mock' | 'websocket' | 'sse';
  transportUrl: string;
  mockScenario: 'happy-path' | 'slow-response' | 'error-response' | 'stream-error-midway';
  launcherLabel: string;
  welcomeMessage: string;
  shadowMode: 'open' | 'closed';
}
