#!/usr/bin/env python
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path.cwd().resolve()
EXPECTED_BRANCH = "review/knowledge-management-phase-2"
GIT = r"C:\Program Files\Git\cmd\git.exe"

TARGET = ROOT / "frontend/src/components/knowledge/knowledge-document-actions.tsx"


def run(
    args: list[str],
    *,
    cwd: Path = ROOT,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print("RUNNING=" + " ".join(args))
    completed = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed


def replace_once(
    text: str,
    old: str,
    new: str,
    label: str,
) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{label}: expected 1 match, found {count}."
        )
    print("PATCHED=" + label)
    return text.replace(old, new, 1)


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
        f"Expected branch {EXPECTED_BRANCH}, found {branch}."
    )

text = TARGET.read_text(
    encoding="utf-8",
).replace("\r\n", "\n")

text = replace_once(
    text,
    '''  type FormEvent,
  useEffect,
  useRef,
''',
    '''  type FormEvent,
  useRef,
''',
    "remove-use-effect-import",
)

effect_block = '''  useEffect(() => {
    setAgentId(
      (current) =>
        assignedAgentIds.includes(current)
          ? current
          : assignedAgentIds[0] ?? "",
    );
    setFile(null);
    setSuccess(null);
    setError(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [
    assignedAgentIds,
    knowledgeBaseId,
    tenantId,
  ]);

'''

text = replace_once(
    text,
    effect_block,
    "",
    "remove-state-sync-effect",
)

text = replace_once(
    text,
    '''  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (!agentId || file === null) {
''',
    '''  const effectiveAgentId =
    assignedAgentIds.includes(agentId)
      ? agentId
      : assignedAgentIds[0] ?? "";

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (!effectiveAgentId || file === null) {
''',
    "derive-effective-agent-id",
)

text = replace_once(
    text,
    '''    formData.append("agent_id", agentId);
''',
    '''    formData.append(
      "agent_id",
      effectiveAgentId,
    );
''',
    "submit-effective-agent-id",
)

text = replace_once(
    text,
    '''            value={agentId}
''',
    '''            value={effectiveAgentId}
''',
    "select-effective-agent-id",
)

text = replace_once(
    text,
    '''            !agentId ||
            file === null
''',
    '''            !effectiveAgentId ||
            file === null
''',
    "button-effective-agent-id",
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

print("\n=== TARGETED ESLINT ===")
lint = run(
    [
        "node",
        "--max-old-space-size=4096",
        r".\node_modules\eslint\bin\eslint.js",
        r"src\components\knowledge\knowledge-bases-view.tsx",
        r"src\components\knowledge\knowledge-document-actions.tsx",
        r"src\app\api\knowledge-bases\[tenantId]\[knowledgeBaseId]\documents\route.ts",
        r"src\app\api\knowledge-bases\[tenantId]\[knowledgeBaseId]\documents\[documentId]\replace\route.ts",
        r"src\lib\server\admin-api.ts",
        r"src\lib\knowledge\contracts.ts",
    ],
    cwd=frontend,
    check=False,
)
print(f"FRONTEND_KNOWLEDGE_UI_FIX_LINT_EXIT={lint.returncode}")
if lint.returncode != 0:
    raise SystemExit(lint.returncode)

print("\n=== TYPESCRIPT CHECK ===")
tsc = run(
    [
        "node",
        "--max-old-space-size=4096",
        r".\node_modules\typescript\bin\tsc",
        "--noEmit",
    ],
    cwd=frontend,
    check=False,
)
print(f"FRONTEND_KNOWLEDGE_UI_FIX_TSC_EXIT={tsc.returncode}")
if tsc.returncode != 0:
    raise SystemExit(tsc.returncode)

print("\n=== API CLIENT DRIFT ===")
drift = run(
    [
        "node",
        r".\scripts\check-api-clients.mjs",
    ],
    cwd=frontend,
    check=False,
)
print(f"FRONTEND_KNOWLEDGE_UI_FIX_DRIFT_EXIT={drift.returncode}")
if drift.returncode != 0:
    raise SystemExit(drift.returncode)

print("\n=== DIFF CHECK ===")
diff = run(
    [GIT, "diff", "--check"],
    check=False,
)
print(f"FRONTEND_KNOWLEDGE_UI_FIX_DIFF_EXIT={diff.returncode}")
if diff.returncode != 0:
    raise SystemExit(diff.returncode)

print("\n=== STATUS ===")
run(
    [
        GIT,
        "status",
        "--short",
        "--untracked-files=all",
    ],
)

print("FRONTEND_KNOWLEDGE_UI_FIX=PASSED")
print("PRODUCTION_BUILD_RUN=False")
print("VISUAL_ACCEPTANCE_RUN=False")
print("FILES_STAGED=False")
print("FILES_COMMITTED=False")
