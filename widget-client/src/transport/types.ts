import type { RuntimeWidgetConfig } from '../config/types.js';

/** Status of the connection to the backend. */
export type ConnectionStatus =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'error';

/** A message sent to the agent selected by the signed Widget session. */
export interface OutgoingMessage {
  text: string;
}

/** Safe error information surfaced from the transport layer. */
export interface TransportError {
  code: string;
  message: string;
  retryable: boolean;
}

export interface MessageCallbacks {
  onChunk(text: string): void;
  onDone(): void;
  onError(error: TransportError): void;
}

/** Transport boundary used by both the live HTTP and local mock clients. */
export interface ITransport {
  /**
   * Establish a session. Live transports return trusted runtime presentation
   * from the bootstrap API; mock transports return no override.
   */
  connect(): Promise<RuntimeWidgetConfig | undefined>;

  /** Send one message and return a cancellation function. */
  send(message: OutgoingMessage, callbacks: MessageCallbacks): () => void;

  /** Tear down the connection and erase in-memory session credentials. */
  disconnect(): void;

  /** Register a listener for connection status changes. */
  onStatusChange(listener: (status: ConnectionStatus) => void): void;
}
