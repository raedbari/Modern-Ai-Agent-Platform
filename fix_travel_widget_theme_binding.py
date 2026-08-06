#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd().resolve()
TARGET = ROOT / "frontend" / "public" / "travel-widget-demo.html"

if not TARGET.is_file():
    raise SystemExit(
        f"Demo page not found: {TARGET}"
    )

text = TARGET.read_text(
    encoding="utf-8",
).replace("\r\n", "\n")

STYLE_MARKER = "/* ATHKA_WIDGET_THEME_BINDING */"

theme_css = r'''
/* ATHKA_WIDGET_THEME_BINDING */
:root {
  --widget-primary: #2563EB;
  --widget-text: #FFFFFF;
  --widget-launcher: #2563EB;
  --widget-header: #2563EB;
  --widget-user: #2563EB;
  --widget-panel: #FFFFFF;
  --widget-surface: #F8F9FC;
  --widget-border: #E5E7EB;
  --widget-input: #FFFFFF;
  --widget-input-text: #111827;
  --widget-bot: #EEF0F5;
  --widget-bot-text: #111827;
}

#launcher {
  color: var(--widget-text) !important;
  background: var(--widget-launcher) !important;
}

#panel {
  border-color: var(--widget-border) !important;
  background: var(--widget-panel) !important;
}

.chatHead {
  color: var(--widget-text) !important;
  background: var(--widget-header) !important;
}

#messages {
  background: var(--widget-surface) !important;
}

.msg.bot {
  color: var(--widget-bot-text) !important;
  background: var(--widget-bot) !important;
}

.msg.user {
  color: var(--widget-text) !important;
  background: var(--widget-user) !important;
}

#form {
  border-color: var(--widget-border) !important;
  background: var(--widget-panel) !important;
}

#input {
  border-color: var(--widget-border) !important;
  background: var(--widget-input) !important;
  color: var(--widget-input-text) !important;
}

#send {
  color: var(--widget-text) !important;
  background: var(--widget-primary) !important;
}
'''

if STYLE_MARKER not in text:
    if "</style>" not in text:
        raise SystemExit(
            "Could not locate </style> in demo page."
        )

    text = text.replace(
        "</style>",
        theme_css + "\n</style>",
        1,
    )
    print("PATCHED=theme-css-binding")
else:
    print("SKIPPED=theme-css-binding-already-present")

FUNCTION_MARKER = "function applyWidgetTheme(theme)"

theme_js = r'''
  function applyWidgetTheme(theme) {
    if (!theme) {
      return;
    }

    const primary =
      theme.primaryColor ||
      theme.primary_color ||
      "#2563EB";

    const textColor =
      theme.textColor ||
      theme.text_color ||
      "#FFFFFF";

    const launcherColor =
      theme.launcherColor ||
      theme.launcher_color ||
      primary;

    const headerColor =
      theme.headerColor ||
      theme.header_color ||
      primary;

    const userMessageColor =
      theme.userMessageColor ||
      theme.user_message_color ||
      primary;

    const position =
      theme.position === "left"
        ? "left"
        : "right";

    const appearance =
      theme.appearance === "dark"
        ? "dark"
        : "light";

    const root =
      document.documentElement.style;

    root.setProperty(
      "--widget-primary",
      primary,
    );

    root.setProperty(
      "--widget-text",
      textColor,
    );

    root.setProperty(
      "--widget-launcher",
      launcherColor,
    );

    root.setProperty(
      "--widget-header",
      headerColor,
    );

    root.setProperty(
      "--widget-user",
      userMessageColor,
    );

    if (appearance === "dark") {
      root.setProperty(
        "--widget-panel",
        "#11131D",
      );
      root.setProperty(
        "--widget-surface",
        "#171A26",
      );
      root.setProperty(
        "--widget-border",
        "#2A2E3D",
      );
      root.setProperty(
        "--widget-input",
        "#1B1E2B",
      );
      root.setProperty(
        "--widget-input-text",
        "#F5F7FF",
      );
      root.setProperty(
        "--widget-bot",
        "#242837",
      );
      root.setProperty(
        "--widget-bot-text",
        "#F5F7FF",
      );
    } else {
      root.setProperty(
        "--widget-panel",
        "#FFFFFF",
      );
      root.setProperty(
        "--widget-surface",
        "#F8F9FC",
      );
      root.setProperty(
        "--widget-border",
        "#E5E7EB",
      );
      root.setProperty(
        "--widget-input",
        "#FFFFFF",
      );
      root.setProperty(
        "--widget-input-text",
        "#111827",
      );
      root.setProperty(
        "--widget-bot",
        "#EEF0F5",
      );
      root.setProperty(
        "--widget-bot-text",
        "#111827",
      );
    }

    if (position === "left") {
      launcher.style.left = "24px";
      launcher.style.right = "auto";
      panel.style.left = "24px";
      panel.style.right = "auto";
    } else {
      launcher.style.right = "24px";
      launcher.style.left = "auto";
      panel.style.right = "24px";
      panel.style.left = "auto";
    }
  }

'''

if FUNCTION_MARKER not in text:
    anchor = '''  function add(role, text) {
'''

    if anchor not in text:
        raise SystemExit(
            "Could not locate widget add() function."
        )

    text = text.replace(
        anchor,
        theme_js + anchor,
        1,
    )
    print("PATCHED=theme-js-binding")
else:
    print("SKIPPED=theme-js-binding-already-present")

CALL_MARKER = "applyWidgetTheme("

if CALL_MARKER not in text:
    anchor = '''    bootstrap = p;
    name.textContent =
'''

    replacement = '''    bootstrap = p;
    applyWidgetTheme(
      p.widget && p.widget.theme,
    );
    name.textContent =
'''

    if anchor not in text:
        raise SystemExit(
            "Could not locate bootstrap assignment."
        )

    text = text.replace(
        anchor,
        replacement,
        1,
    )
    print("PATCHED=bootstrap-theme-application")
else:
    print("SKIPPED=bootstrap-theme-application-already-present")

TARGET.write_text(
    text.rstrip("\n") + "\n",
    encoding="utf-8",
    newline="\n",
)

print(f"WROTE={TARGET}")
print("WIDGET_THEME_BINDING=READY")
print("REBUILD_REQUIRED=False")
print("HARD_REFRESH_REQUIRED=True")
print("FILES_STAGED=False")
print("FILES_COMMITTED=False")
