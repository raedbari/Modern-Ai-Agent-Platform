"use client";

import {
  Bot,
  Loader2,
  Send,
} from "lucide-react";

import {
  type FormEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import type {
  WidgetTheme,
} from "@/lib/widget-settings/contracts";

type LiveWidgetPreviewProps = {
  publicWidgetId: string | null;
  displayName: string;
  greeting: string;
  theme: WidgetTheme;
  isEnabled: boolean;
};

type PreviewMessage = {
  id: string;
  role: "assistant" | "user" | "error";
  text: string;
};

type BootstrapPayload = {
  session_token?: unknown;
};

type ChatPayload = {
  conversation_id?: unknown;
  reply?: unknown;
};

const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

function messageId(): string {
  return `${
    Date.now()
  }-${
    Math.random().toString(36).slice(2)
  }`;
}

async function responseDetail(
  response: Response,
): Promise<string> {
  const payload = await response
    .json()
    .catch(() => null) as {
      detail?: unknown;
    } | null;

  if (
    typeof payload?.detail === "string" &&
    payload.detail.trim()
  ) {
    return payload.detail;
  }

  return `HTTP ${response.status}`;
}

export function LiveWidgetPreview({
  publicWidgetId,
  displayName,
  greeting,
  theme,
  isEnabled,
}: LiveWidgetPreviewProps) {
  const tokenRef = useRef<string | null>(
    null,
  );
  const conversationIdRef =
    useRef<string | null>(null);
  const messagesRef =
    useRef<HTMLDivElement | null>(null);

  const [messages, setMessages] = useState<
    PreviewMessage[]
  >([
    {
      id: "greeting",
      role: "assistant",
      text: greeting,
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<
    "offline" | "connecting" | "online" | "error"
  >("offline");

  const bootstrap = useCallback(
    async (
      signal?: AbortSignal,
    ): Promise<string> => {
      if (!publicWidgetId) {
        throw new Error(
          "احفظ إعدادات الويدجت أولًا.",
        );
      }

      if (!isEnabled) {
        throw new Error(
          "الويدجت معطل حاليًا.",
        );
      }

      setStatus("connecting");

      const response = await fetch(
        `${API_BASE}/api/widget/bootstrap`,
        {
          method: "POST",
          signal,
          cache: "no-store",
          headers: {
            "Content-Type":
              "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            widget_id: publicWidgetId,
          }),
        },
      );

      if (!response.ok) {
        throw new Error(
          await responseDetail(response),
        );
      }

      const payload =
        await response.json() as BootstrapPayload;

      if (
        typeof payload.session_token !==
          "string" ||
        !payload.session_token
      ) {
        throw new Error(
          "لم يُرجع Bootstrap جلسة صالحة.",
        );
      }

      tokenRef.current =
        payload.session_token;
      setStatus("online");

      return payload.session_token;
    },
    [
      isEnabled,
      publicWidgetId,
    ],
  );

  useEffect(() => {
    tokenRef.current = null;
    conversationIdRef.current = null;
    setInput("");
    setBusy(false);
    setMessages([
      {
        id: "greeting",
        role: "assistant",
        text: greeting,
      },
    ]);

    if (!publicWidgetId || !isEnabled) {
      setStatus("offline");
      return;
    }

    const controller =
      new AbortController();

    void bootstrap(controller.signal).catch(
      (error: unknown) => {
        if (
          error instanceof DOMException &&
          error.name === "AbortError"
        ) {
          return;
        }

        setStatus("error");
      },
    );

    return () => {
      controller.abort();
    };
  }, [
    bootstrap,
    greeting,
    isEnabled,
    publicWidgetId,
  ]);

  useEffect(() => {
    const node = messagesRef.current;

    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages]);

  async function sendChat(
    token: string,
    message: string,
  ): Promise<Response> {
    const body: {
      message: string;
      conversation_id?: string;
    } = {
      message,
    };

    if (conversationIdRef.current) {
      body.conversation_id =
        conversationIdRef.current;
    }

    return fetch(
      `${API_BASE}/api/chat`,
      {
        method: "POST",
        cache: "no-store",
        headers: {
          "Content-Type":
            "application/json",
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      },
    );
  }

  async function submit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const message = input.trim();

    if (!message || busy) {
      return;
    }

    setInput("");
    setBusy(true);
    setMessages((current) => [
      ...current,
      {
        id: messageId(),
        role: "user",
        text: message,
      },
    ]);

    try {
      let token =
        tokenRef.current ??
        await bootstrap();

      let response =
        await sendChat(token, message);

      if (response.status === 401) {
        tokenRef.current = null;
        conversationIdRef.current = null;
        token = await bootstrap();
        response =
          await sendChat(token, message);
      }

      if (!response.ok) {
        throw new Error(
          await responseDetail(response),
        );
      }

      const payload =
        await response.json() as ChatPayload;

      if (
        typeof payload.conversation_id ===
        "string"
      ) {
        conversationIdRef.current =
          payload.conversation_id;
      }

      if (
        typeof payload.reply !== "string" ||
        !payload.reply.trim()
      ) {
        throw new Error(
          "وصل رد فارغ من المحادثة.",
        );
      }

      setMessages((current) => [
        ...current,
        {
          id: messageId(),
          role: "assistant",
          text: payload.reply as string,
        },
      ]);
      setStatus("online");
    } catch (error) {
      setStatus("error");
      setMessages((current) => [
        ...current,
        {
          id: messageId(),
          role: "error",
          text:
            error instanceof Error
              ? error.message
              : "تعذر إرسال الرسالة.",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  const statusText =
    status === "online"
      ? "متصل"
      : status === "connecting"
        ? "جارٍ الاتصال"
        : status === "error"
          ? "تعذر الاتصال"
          : "غير متصل";

  const inputDisabled =
    busy ||
    !publicWidgetId ||
    !isEnabled;

  return (
    <div className="widget-settings-chat-window">
      <header
        style={{
          backgroundColor:
            theme.headerColor,
          color: theme.textColor,
        }}
      >
        <span className="widget-settings-chat-avatar">
          <Bot aria-hidden="true" />
        </span>

        <span>
          <strong>{displayName}</strong>

          <small>
            <i />
            {statusText}
          </small>
        </span>
      </header>

      <div
        ref={messagesRef}
        className="widget-settings-chat-body"
        style={{
          overflowY: "auto",
          minHeight: 0,
        }}
      >
        {messages.map((message) => (
          <div
            key={message.id}
            className={
              message.role === "user"
                ? (
                  "widget-settings-chat-message "
                  + "widget-settings-chat-message--user"
                )
                : (
                  "widget-settings-chat-message "
                  + "widget-settings-chat-message--assistant"
                )
            }
            style={
              message.role === "user"
                ? {
                  backgroundColor:
                    theme.userMessageColor,
                  color:
                    theme.textColor,
                }
                : message.role === "error"
                  ? {
                    border:
                      "1px solid rgba(248,113,113,.45)",
                    color: "#FCA5A5",
                  }
                  : undefined
            }
          >
            {message.text}
          </div>
        ))}

        {busy && (
          <div className="widget-settings-chat-message widget-settings-chat-message--assistant">
            <Loader2
              aria-label="جارٍ إنشاء الرد"
              style={{
                width: 18,
                height: 18,
                animation:
                  "widget-settings-spin 1s linear infinite",
              }}
            />
          </div>
        )}
      </div>

      <form
        onSubmit={(event) => {
          void submit(event);
        }}
        style={{
          display: "flex",
          alignItems: "center",
          flexDirection: "row",
          direction: "rtl",
          gap: 10,
          width: "100%",
          flex: "0 0 auto",
          margin: 0,
          padding: 12,
          borderTop:
            theme.appearance === "dark"
              ? "1px solid rgba(148,163,184,.18)"
              : "1px solid rgba(15,23,42,.12)",
          backgroundColor:
            theme.appearance === "dark"
              ? "rgba(17,19,29,.98)"
              : "#FFFFFF",
        }}
      >
          <input
            type="text"
            dir="auto"
            value={input}
            disabled={inputDisabled}
            placeholder={
              publicWidgetId
                ? "اكتب رسالتك..."
                : "احفظ الإعدادات أولًا"
            }
            aria-label="رسالة المعاينة المباشرة"
            autoComplete="off"
            onChange={(event) => {
              setInput(event.target.value);
            }}
            style={{
              flex: "1 1 auto",
              minWidth: 0,
              width: "100%",
              height: 44,
              border:
                theme.appearance === "dark"
                  ? "1px solid rgba(148,163,184,.24)"
                  : "1px solid rgba(15,23,42,.14)",
              borderRadius: 12,
              outline: 0,
              padding: "0 12px",
              backgroundColor:
                theme.appearance === "dark"
                  ? "rgba(31,35,49,.96)"
                  : "#FFFFFF",
              color:
                theme.appearance === "dark"
                  ? "#F8FAFC"
                  : "#111827",
              font: "inherit",
              textAlign: "right",
            }}
          />

          <button
            type="submit"
            title="إرسال"
            disabled={
              inputDisabled ||
              !input.trim()
            }
            style={{
              display: "grid",
              width: 44,
              height: 44,
              flex: "0 0 44px",
              placeItems: "center",
              margin: 0,
              padding: 0,
              border: 0,
              borderRadius: 12,
              backgroundColor:
                theme.primaryColor,
              color: theme.textColor,
              opacity:
                inputDisabled ||
                !input.trim()
                  ? 0.55
                  : 1,
              cursor:
                inputDisabled ||
                !input.trim()
                  ? "not-allowed"
                  : "pointer",
            }}
          >
            {busy ? (
              <Loader2
                aria-hidden="true"
                style={{
                  animation:
                    "widget-settings-spin 1s linear infinite",
                }}
              />
            ) : (
              <Send aria-hidden="true" />
            )}
          </button>
      </form>
    </div>
  );
}
