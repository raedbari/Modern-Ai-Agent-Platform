/** Status of the connection to the backend. */
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

/** A message sent from the widget to the agent. */
export interface OutgoingMessage {
  /** User's text input. */
  text: string;
  /** Agent ID to route the message to. */
  agentId: string;
  /** Optional conversation thread identifier. */
  threadId?: string;
}

/** Error information surfaced from the transport layer. */
export interface TransportError {
  code: string;
  message: string;
  retryable: boolean;
}

/** Callbacks provided to ITransport when sending a message. */
export interface MessageCallbacks {
  /** Fired for each streamed chunk of text from the assistant. */
  onChunk(text: string): void;
  /** Fired when the assistant response is complete. */
  onDone(): void;
  /** Fired when an error occurs. */
  onError(error: TransportError): void;
}

/**
 * ITransport — the contract that every transport implementation must satisfy.
 *
 * The widget UI layer depends only on this interface, never on concrete classes.
 */
export interface ITransport {
  /**
   * Establish or verify the connection.
   * Must resolve once the transport is ready to send messages.
   */
  connect(): Promise<void>;

  /**
   * Send a user message and stream the response via callbacks.
   * Returns a cancel function; calling it stops streaming.
   */
  send(message: OutgoingMessage, callbacks: MessageCallbacks): () => void;

  /** Tear down the connection and release resources. */
  disconnect(): void;

  /** Register a listener for connection status changes. */
  onStatusChange(listener: (status: ConnectionStatus) => void): void;
}
