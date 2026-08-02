import type {
  ITransport,
  OutgoingMessage,
  MessageCallbacks,
  ConnectionStatus,
} from '../types.js';
import type { ResolvedConfig } from '../../config/types.js';
import { runHappyPath } from './scenarios/happy-path.js';
import { runSlowResponse } from './scenarios/slow-response.js';
import { runErrorResponse } from './scenarios/error-response.js';
import { runStreamErrorMidway } from './scenarios/stream-error-midway.js';

type Scenario = ResolvedConfig['mockScenario'];
type StatusListener = (status: ConnectionStatus) => void;

/**
 * MockTransport — a fully in-memory ITransport implementation.
 *
 * Enables UI development and testing without a real backend.
 * The active scenario determines the streaming behaviour.
 */
export class MockTransport implements ITransport {
  readonly #scenario: Scenario;
  #status: ConnectionStatus = 'disconnected';
  #statusListeners: StatusListener[] = [];
  #activeCancelFn: (() => void) | null = null;

  constructor(scenario: Scenario = 'happy-path') {
    this.#scenario = scenario;
  }

  getStatus(): ConnectionStatus {
    return this.#status;
  }

  async connect(): Promise<undefined> {
    this.#setStatus('connecting');
    // Simulate a brief async handshake
    await new Promise<void>((resolve) => setTimeout(resolve, 10));
    this.#setStatus('connected');
    return undefined;
  }

  send(_message: OutgoingMessage, callbacks: MessageCallbacks): () => void {
    // Cancel any existing in-flight request
    this.#activeCancelFn?.();

    const cancel = this.#runScenario(callbacks);
    this.#activeCancelFn = cancel;

    return () => {
      cancel();
      this.#activeCancelFn = null;
    };
  }

  disconnect(): void {
    this.#activeCancelFn?.();
    this.#activeCancelFn = null;
    this.#setStatus('disconnected');
  }

  onStatusChange(listener: StatusListener): void {
    this.#statusListeners.push(listener);
  }

  // ─── Private helpers ──────────────────────────────────────────────────────

  #runScenario(callbacks: MessageCallbacks): () => void {
    switch (this.#scenario) {
      case 'happy-path':
        return runHappyPath(callbacks);
      case 'slow-response':
        return runSlowResponse(callbacks);
      case 'error-response':
        return runErrorResponse(callbacks);
      case 'stream-error-midway':
        return runStreamErrorMidway(callbacks);
      default: {
        const _exhaustive: never = this.#scenario;
        throw new Error(`Unknown mock scenario: ${String(_exhaustive)}`);
      }
    }
  }

  #setStatus(status: ConnectionStatus): void {
    this.#status = status;
    for (const listener of this.#statusListeners) {
      listener(status);
    }
  }
}
