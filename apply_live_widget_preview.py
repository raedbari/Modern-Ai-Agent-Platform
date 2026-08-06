#!/usr/bin/env python
from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path.cwd().resolve()
GIT = r"C:\Program Files\Git\cmd\git.exe"

VIEW = (
    ROOT
    / "frontend"
    / "src"
    / "components"
    / "widget-settings"
    / "widget-settings-view.tsx"
)
LIVE_PREVIEW = (
    ROOT
    / "frontend"
    / "src"
    / "components"
    / "widget-settings"
    / "live-widget-preview.tsx"
)

EXPECTED_BRANCH = "review/knowledge-management-phase-2"


def run(
    args: list[str],
    *,
    cwd: Path = ROOT,
) -> subprocess.CompletedProcess[str]:
    print("RUNNING=" + " ".join(args))
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result


def read_lf(path: Path) -> str:
    return path.read_text(
        encoding="utf-8",
    ).replace("\r\n", "\n")


def write_lf(path: Path, content: str) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        content.rstrip("\n") + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        "WROTE="
        + path.relative_to(ROOT).as_posix()
    )


branch = subprocess.run(
    [GIT, "branch", "--show-current"],
    cwd=ROOT,
    text=True,
    encoding="utf-8",
    capture_output=True,
    check=True,
).stdout.strip()

print(f"CURRENT_BRANCH={branch}")

if branch != EXPECTED_BRANCH:
    raise SystemExit(
        "Expected branch "
        f"{EXPECTED_BRANCH}, found {branch}."
    )

if not VIEW.is_file():
    raise SystemExit(
        f"Missing target file: {VIEW}"
    )

component_source = r'''"use client";

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
      >
        <footer>
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
              flex: 1,
              minWidth: 0,
              border: 0,
              outline: 0,
              background: "transparent",
              color: "inherit",
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
              backgroundColor:
                theme.primaryColor,
              color: theme.textColor,
              opacity:
                inputDisabled ||
                !input.trim()
                  ? 0.55
                  : 1,
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
        </footer>
      </form>
    </div>
  );
}
'''

if LIVE_PREVIEW.exists():
    existing = read_lf(LIVE_PREVIEW)
    if existing != component_source:
        raise SystemExit(
            "Live preview component already exists "
            "with unexpected content."
        )
    print(
        "SKIPPED=live-preview-component-"
        "already-current"
    )
else:
    write_lf(
        LIVE_PREVIEW,
        component_source,
    )

view = read_lf(VIEW)

import_anchor = '''import {
  createDefaultWidgetPayload,
} from "@/lib/widget-settings/contracts";
'''

live_import = '''import {
  LiveWidgetPreview,
} from "@/components/widget-settings/live-widget-preview";

import {
  createDefaultWidgetPayload,
} from "@/lib/widget-settings/contracts";
'''

if (
    'from "@/components/widget-settings/live-widget-preview";'
    not in view
):
    if import_anchor not in view:
        raise SystemExit(
            "Could not locate widget contracts "
            "import anchor."
        )
    view = view.replace(
        import_anchor,
        live_import,
        1,
    )
    print("PATCHED=live-preview-import")

static_pattern = re.compile(
    r'''              <div className="widget-settings-chat-window">'''
    r'''.*?'''
    r'''(?=\n              <button\n'''
    r'''                type="button"\n'''
    r'''                className="widget-settings-launcher")''',
    re.DOTALL,
)

live_markup = '''              <LiveWidgetPreview
                publicWidgetId={
                  publicWidgetId
                }
                displayName={previewName}
                greeting={previewGreeting}
                theme={draft.theme}
                isEnabled={draft.is_enabled}
              />
'''

if "<LiveWidgetPreview" not in view:
    matches = list(
        static_pattern.finditer(view)
    )
    if len(matches) != 1:
        raise SystemExit(
            "Expected exactly one static preview "
            f"block, found {len(matches)}."
        )
    view = static_pattern.sub(
        live_markup.rstrip("\n"),
        view,
        count=1,
    )
    print(
        "PATCHED=static-preview-to-live-chat"
    )
else:
    print(
        "SKIPPED=static-preview-already-live"
    )

if "  Send,\n" in view:
    view = view.replace(
        "  Send,\n",
        "",
        1,
    )
    print(
        "PATCHED=remove-unused-parent-send-import"
    )

write_lf(VIEW, view)

frontend = ROOT / "frontend"

run(
    [
        "node",
        "--max-old-space-size=4096",
        r".\node_modules\eslint\bin\eslint.js",
        r"src\components\widget-settings\widget-settings-view.tsx",
        r"src\components\widget-settings\live-widget-preview.tsx",
    ],
    cwd=frontend,
)

run(
    [
        "node",
        "--max-old-space-size=4096",
        r".\node_modules\typescript\bin\tsc",
        "--noEmit",
    ],
    cwd=frontend,
)

run(
    [
        "node",
        r".\scripts\check-api-clients.mjs",
    ],
    cwd=frontend,
)

run(
    [
        GIT,
        "diff",
        "--check",
    ],
)

print("")
print("LIVE_WIDGET_PREVIEW_IMPLEMENTATION=PASSED")
print("TARGET_WIDGET_ID_IS_DYNAMIC=True")
print("REAL_BOOTSTRAP_AND_CHAT=True")
print("FILES_STAGED=False")
print("FILES_COMMITTED=False")
print("PRODUCTION_REBUILD_REQUIRED=True")
