#!/usr/bin/env python
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path.cwd().resolve()
TARGET = ROOT / "frontend" / "public" / "travel-widget-demo.html"

if not TARGET.is_file():
    raise SystemExit(f"Demo page not found: {TARGET}")

text = TARGET.read_text(
    encoding="utf-8",
).replace("\r\n", "\n")

if "function applyWidgetTheme(theme)" not in text:
    raise SystemExit(
        "Theme function is missing. Run the previous theme-binding patch first."
    )

if "/* ATHKA_WIDGET_THEME_BINDING */" not in text:
    raise SystemExit(
        "Theme CSS binding is missing. Run the previous theme-binding patch first."
    )

call_pattern = re.compile(
    r"applyWidgetTheme\s*\(\s*"
    r"p\.widget\s*&&\s*p\.widget\.theme\s*,?\s*"
    r"\)\s*;"
)

if call_pattern.search(text):
    print("SKIPPED=bootstrap-theme-call-already-present")
else:
    assignment_pattern = re.compile(
        r"(?P<indent>^[ \t]*)bootstrap\s*=\s*p\s*;\s*$",
        re.MULTILINE,
    )

    matches = list(assignment_pattern.finditer(text))

    if len(matches) != 1:
        raise SystemExit(
            "bootstrap assignment: expected 1 match, "
            f"found {len(matches)}."
        )

    match = matches[0]
    indent = match.group("indent")
    insertion = (
        match.group(0)
        + "\n"
        + indent
        + "applyWidgetTheme(\n"
        + indent
        + "  p.widget && p.widget.theme,\n"
        + indent
        + ");"
    )

    text = (
        text[:match.start()]
        + insertion
        + text[match.end():]
    )

    print("PATCHED=bootstrap-theme-call")

TARGET.write_text(
    text.rstrip("\n") + "\n",
    encoding="utf-8",
    newline="\n",
)

verified = TARGET.read_text(
    encoding="utf-8",
).replace("\r\n", "\n")

if not call_pattern.search(verified):
    raise SystemExit(
        "Theme call verification failed."
    )

print(f"WROTE={TARGET}")
print("THEME_FUNCTION_PRESENT=True")
print("THEME_CSS_PRESENT=True")
print("THEME_BOOTSTRAP_CALL_PRESENT=True")
print("REBUILD_REQUIRED=False")
print("HARD_REFRESH_REQUIRED=True")
print("WIDGET_THEME_RUNTIME_FIX_V2=PASSED")
