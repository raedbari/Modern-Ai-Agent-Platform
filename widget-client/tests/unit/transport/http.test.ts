import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest';
import { HttpTransport } from '../../../src/transport/http/HttpTransport.js';
import type {
  MessageCallbacks,
  TransportError,
} from '../../../src/transport/types.js';

const SERVER_URL = 'https://ai.travel-x.online';
const WIDGET_ID = `wgt_${'a'.repeat(20)}`;

function bootstrapResponse(token = 'signed-widget-token'): Response {
  return jsonResponse({
    session_token: token,
    token_type: 'Bearer',
    expires_in: 600,
    session_id: 'session-1',
    widget: {
      widget_id: WIDGET_ID,
      display_name: 'Kiwi Support',
      greeting: 'How can we help?',
      theme: {
        primaryColor: '#112233',
        textColor: '#FFFFFF',
        launcherColor: '#223344',
        headerColor: '#334455',
        userMessageColor: '#445566',
        position: 'left',
        appearance: 'dark',
      },
    },
  });
}

function chatResponse(
  conversationId = 'conversation-1',
  reply = 'Hello from the agent',
): Response {
  return jsonResponse({
    conversation_id: conversationId,
    message_id: 'message-1',
    reply,
    model: 'test-model',
    usage: { prompt: 1, completion: 1 },
    answer_status: 'generated',
    sources: [],
  });
}

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

async function send(
  transport: HttpTransport,
  text: string,
): Promise<{ chunks: string[]; error?: TransportError }> {
  const chunks: string[] = [];
  return new Promise((resolve) => {
    const callbacks: MessageCallbacks = {
      onChunk: (chunk) => chunks.push(chunk),
      onDone: () => resolve({ chunks }),
      onError: (error) => resolve({ chunks, error }),
    };
    transport.send({ text }, callbacks);
  });
}

describe('HttpTransport', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('bootstraps the opaque Widget ID and maps trusted presentation', async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(bootstrapResponse());
    const statuses: string[] = [];
    const transport = new HttpTransport({
      serverUrl: SERVER_URL,
      widgetId: WIDGET_ID,
    });
    transport.onStatusChange((status) => statuses.push(status));

    const runtime = await transport.connect();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${SERVER_URL}/api/widget/bootstrap`);
    expect(init?.credentials).toBe('omit');
    expect(JSON.parse(String(init?.body))).toEqual({ widget_id: WIDGET_ID });
    expect(runtime).toEqual({
      displayName: 'Kiwi Support',
      welcomeMessage: 'How can we help?',
      theme: {
        primary: '#112233',
        onPrimary: '#FFFFFF',
        launcherBg: '#223344',
        headerBg: '#334455',
        userBubbleBg: '#445566',
      },
      position: 'left',
      appearance: 'dark',
    });
    expect(statuses).toEqual(['connecting', 'connected']);
  });

  it('uses only the bearer session for chat and reuses conversation_id', async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(bootstrapResponse())
      .mockResolvedValueOnce(chatResponse())
      .mockResolvedValueOnce(chatResponse('conversation-1', 'Second reply'));
    const transport = new HttpTransport({
      serverUrl: SERVER_URL,
      widgetId: WIDGET_ID,
    });
    await transport.connect();

    expect(await send(transport, 'First question')).toEqual({
      chunks: ['Hello from the agent'],
    });
    expect(await send(transport, 'Second question')).toEqual({
      chunks: ['Second reply'],
    });

    const firstChat = fetchMock.mock.calls[1][1];
    const secondChat = fetchMock.mock.calls[2][1];
    expect(firstChat?.headers).toEqual({
      Authorization: 'Bearer signed-widget-token',
      'Content-Type': 'application/json',
    });
    expect(JSON.parse(String(firstChat?.body))).toEqual({
      message: 'First question',
    });
    expect(JSON.parse(String(secondChat?.body))).toEqual({
      message: 'Second question',
      conversation_id: 'conversation-1',
    });
    expect(String(firstChat?.body)).not.toContain('agent');
  });

  it('re-bootstraps once after a 401 and retries with the new token', async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(bootstrapResponse('token-1'))
      .mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, 401))
      .mockResolvedValueOnce(bootstrapResponse('token-2'))
      .mockResolvedValueOnce(chatResponse());
    const transport = new HttpTransport({
      serverUrl: SERVER_URL,
      widgetId: WIDGET_ID,
    });
    await transport.connect();

    const result = await send(transport, 'Retry me');

    expect(result.error).toBeUndefined();
    expect(fetchMock).toHaveBeenCalledTimes(4);
    expect(fetchMock.mock.calls[3][1]?.headers).toEqual({
      Authorization: 'Bearer token-2',
      'Content-Type': 'application/json',
    });
  });

  it('returns a safe rate-limit message without exposing API details', async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(bootstrapResponse())
      .mockResolvedValueOnce(
        jsonResponse({ detail: 'internal limiter bucket name' }, 429),
      );
    const transport = new HttpTransport({
      serverUrl: SERVER_URL,
      widgetId: WIDGET_ID,
    });
    const statuses: string[] = [];
    transport.onStatusChange((status) => statuses.push(status));
    await transport.connect();

    const result = await send(transport, 'Too fast');

    expect(result.error).toEqual({
      code: 'rate_limited',
      message: 'Too many requests. Please wait a moment and try again.',
      retryable: true,
    });
    expect(result.error?.message).not.toContain('bucket');
    expect(statuses[statuses.length - 1]).toBe('connected');
  });

  it('rejects malformed bootstrap data instead of trusting remote HTML values', async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(jsonResponse({ session_token: '<script>' }));
    const transport = new HttpTransport({
      serverUrl: SERVER_URL,
      widgetId: WIDGET_ID,
    });

    await expect(transport.connect()).rejects.toThrow(
      'Invalid Widget bootstrap response.',
    );
  });
});
