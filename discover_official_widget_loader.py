#!/usr/bin/env python
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path.cwd().resolve()
GIT = r"C:\Program Files\Git\cmd\git.exe"
OUTPUT = Path.home() / "AppData" / "Local" / "Temp" / "athka-official-widget-discovery.txt"


def run_capture(args: list[str], *, cwd: Path = ROOT) -> str:
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    output = completed.stdout
    if completed.stderr:
        output += "\n[stderr]\n" + completed.stderr
    output += f"\n[exit={completed.returncode}]\n"
    return output


def append_section(title: str, content: str) -> None:
    with OUTPUT.open(
        "a",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        handle.write(f"\n=== {title} ===\n")
        handle.write(content.rstrip("\n"))
        handle.write("\n")


def append_file(relative_path: str) -> None:
    path = ROOT / relative_path
    if not path.is_file():
        append_section(
            f"MISSING FILE: {relative_path}",
            "File not found.",
        )
        return

    append_section(
        f"FILE: {relative_path}",
        path.read_text(
            encoding="utf-8",
            errors="replace",
        ),
    )


if not (ROOT / ".git").exists():
    raise SystemExit(
        "Run this script from the repository root."
    )

OUTPUT.write_text(
    "ATHKACHATBOTS OFFICIAL WIDGET DISCOVERY\n",
    encoding="utf-8",
    newline="\n",
)

append_section(
    "REPOSITORY STATE",
    run_capture(
        [
            GIT,
            "branch",
            "--show-current",
        ]
    )
    + run_capture(
        [
            GIT,
            "log",
            "-5",
            "--oneline",
        ]
    )
    + run_capture(
        [
            GIT,
            "status",
            "--short",
            "--untracked-files=all",
        ]
    ),
)

append_section(
    "FRONTEND PUBLIC FILES",
    run_capture(
        [
            GIT,
            "ls-files",
            "frontend/public",
            "frontend/src",
        ]
    ),
)

append_section(
    "WIDGET-RELATED TRACKED FILES",
    run_capture(
        [
            GIT,
            "grep",
            "-n",
            "-E",
            (
                "widget_id|publicWidgetId|"
                "allowed_origins|allowedOrigins|"
                "navigator.clipboard|copy.*embed|"
                "athka-widget|widget/bootstrap|"
                "/api/chat|ShadowRoot|attachShadow"
            ),
            "--",
            "frontend",
            "backend",
        ]
    ),
)

append_section(
    "NEXT CONFIG AND MIDDLEWARE",
    run_capture(
        [
            GIT,
            "ls-files",
            (
                "frontend/next.config.*"
            ),
            (
                "frontend/src/middleware.*"
            ),
            (
                "frontend/src/proxy.*"
            ),
        ]
    ),
)

for file_name in [
    "frontend/src/components/widget-settings/widget-settings-view.tsx",
    "frontend/src/components/widget-settings/live-widget-preview.tsx",
    "frontend/src/lib/widget-settings/contracts.ts",
    "frontend/src/lib/server/admin-api.ts",
    "frontend/package.json",
    "frontend/next.config.ts",
    "frontend/next.config.mjs",
    "frontend/src/proxy.ts",
    "frontend/src/middleware.ts",
    "backend/app/api/routes/widget.py",
    "backend/app/api/routes/chat.py",
    "backend/app/api/schemas/widget.py",
    "backend/app/core/config.py",
]:
    append_file(file_name)

append_section(
    "WIDGET SETTINGS STYLE REFERENCES",
    run_capture(
        [
            GIT,
            "grep",
            "-n",
            "-B",
            "8",
            "-A",
            "28",
            "-E",
            (
                "widget-settings-chat-window|"
                "widget-settings-launcher|"
                "widget-settings-chat-message|"
                "widget-settings.*embed|"
                "widget-settings.*copy"
            ),
            "--",
            "frontend/src",
        ]
    ),
)

append_section(
    "BOOTSTRAP AND CHAT CONTRACTS",
    run_capture(
        [
            GIT,
            "grep",
            "-n",
            "-B",
            "20",
            "-A",
            "90",
            "-E",
            (
                "def bootstrap|"
                "bootstrap_widget|"
                "WidgetBootstrap|"
                "ChatResponse|"
                "session_token|"
                "allowed_origins"
            ),
            "--",
            "backend/app",
            "backend/tests",
        ]
    ),
)

append_section(
    "OPENAPI WIDGET PATHS",
    run_capture(
        [
            str(ROOT / ".venv" / "Scripts" / "python.exe"),
            "-c",
            (
                "import json;"
                "p=json.load(open(r'backend/openapi.json',encoding='utf-8'))['paths'];"
                "[print(m.upper(),k) for k,v in sorted(p.items()) "
                "if ('widget' in k or k=='/api/chat') "
                "for m in v if m in {'get','post','put','patch','delete'}]"
            ),
        ]
    ),
)

append_section(
    "FINAL STATUS",
    run_capture(
        [
            GIT,
            "status",
            "--short",
            "--untracked-files=all",
        ]
    ),
)

print(f"OFFICIAL_WIDGET_DISCOVERY=READY")
print(f"OUTPUT={OUTPUT}")
print(f"SIZE_BYTES={OUTPUT.stat().st_size}")
print("FILES_MODIFIED=False")
