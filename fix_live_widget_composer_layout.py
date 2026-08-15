#!/usr/bin/env python
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path.cwd().resolve()
GIT = r"C:\Program Files\Git\cmd\git.exe"
TARGET = (
    ROOT
    / "frontend"
    / "src"
    / "components"
    / "widget-settings"
    / "live-widget-preview.tsx"
)


def run(
    args: list[str],
    *,
    cwd: Path = ROOT,
) -> None:
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


if not TARGET.is_file():
    raise SystemExit(
        f"Missing target file: {TARGET}"
    )

text = TARGET.read_text(
    encoding="utf-8",
).replace("\r\n", "\n")

old_open = '''      <form
        onSubmit={(event) => {
          void submit(event);
        }}
      >
        <footer>
'''

new_open = '''      <form
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
'''

if old_open not in text:
    raise SystemExit(
        "Could not locate the current composer opening block."
    )

text = text.replace(
    old_open,
    new_open,
    1,
)

old_input_style = '''            style={{
              flex: 1,
              minWidth: 0,
              border: 0,
              outline: 0,
              background: "transparent",
              color: "inherit",
              font: "inherit",
              textAlign: "right",
            }}
'''

new_input_style = '''            style={{
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
'''

if old_input_style not in text:
    raise SystemExit(
        "Could not locate the current input style block."
    )

text = text.replace(
    old_input_style,
    new_input_style,
    1,
)

old_button_style = '''            style={{
              backgroundColor:
                theme.primaryColor,
              color: theme.textColor,
              opacity:
                inputDisabled ||
                !input.trim()
                  ? 0.55
                  : 1,
            }}
'''

new_button_style = '''            style={{
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
'''

if old_button_style not in text:
    raise SystemExit(
        "Could not locate the current send-button style block."
    )

text = text.replace(
    old_button_style,
    new_button_style,
    1,
)

old_close = '''          </button>
        </footer>
      </form>
'''

new_close = '''          </button>
      </form>
'''

if old_close not in text:
    raise SystemExit(
        "Could not locate the current composer closing block."
    )

text = text.replace(
    old_close,
    new_close,
    1,
)

TARGET.write_text(
    text.rstrip("\n") + "\n",
    encoding="utf-8",
    newline="\n",
)

print(
    "WROTE="
    + TARGET.relative_to(ROOT).as_posix()
)

frontend = ROOT / "frontend"

run(
    [
        "node",
        "--max-old-space-size=4096",
        r".\node_modules\eslint\bin\eslint.js",
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
        GIT,
        "diff",
        "--check",
        "--",
        "frontend/src/components/widget-settings/live-widget-preview.tsx",
    ],
)

print("LIVE_WIDGET_COMPOSER_LAYOUT_FIX=PASSED")
print("SEND_BUTTON_PLACEMENT=LEFT")
print("INPUT_PLACEMENT=RIGHT")
print("PRODUCTION_REBUILD_REQUIRED=True")
print("FILES_STAGED=False")
print("FILES_COMMITTED=False")
