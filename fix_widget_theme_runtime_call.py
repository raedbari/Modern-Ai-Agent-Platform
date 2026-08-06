#!/usr/bin/env python
from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd().resolve()
TARGET = ROOT / "frontend" / "public" / "travel-widget-demo.html"

if not TARGET.is_file():
    raise SystemExit(f"Demo page not found: {TARGET}")

text = TARGET.read_text(
    encoding="utf-8",
).replace("\r\n", "\n")

exact_call = '''    applyWidgetTheme(
      p.widget && p.widget.theme,
    );
'''

if exact_call in text:
    print("SKIPPED=bootstrap-theme-call-already-present")
else:
    anchor = '''    bootstrap = p;
    name.textContent =
'''

    replacement = '''    bootstrap = p;
    applyWidgetTheme(
      p.widget && p.widget.theme,
    );
    name.textContent =
'''

    count = text.count(anchor)
    if count != 1:
        raise SystemExit(
            "bootstrap-theme-call: expected 1 anchor, "
            f"found {count}."
        )

    text = text.replace(anchor, replacement, 1)
    print("PATCHED=bootstrap-theme-call")

TARGET.write_text(
    text.rstrip("\n") + "\n",
    encoding="utf-8",
    newline="\n",
)

verified = TARGET.read_text(
    encoding="utf-8",
).replace("\r\n", "\n")

if exact_call not in verified:
    raise SystemExit(
        "Theme call verification failed."
    )

if "function applyWidgetTheme(theme)" not in verified:
    raise SystemExit(
        "Theme function is missing."
    )

if "/* ATHKA_WIDGET_THEME_BINDING */" not in verified:
    raise SystemExit(
        "Theme CSS binding is missing."
    )

print(f"WROTE={TARGET}")
print("THEME_FUNCTION_PRESENT=True")
print("THEME_CSS_PRESENT=True")
print("THEME_BOOTSTRAP_CALL_PRESENT=True")
print("REBUILD_REQUIRED=False")
print("HARD_REFRESH_REQUIRED=True")
print("WIDGET_THEME_RUNTIME_FIX=PASSED")
