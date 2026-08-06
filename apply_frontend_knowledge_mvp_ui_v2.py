#!/usr/bin/env python
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path.cwd().resolve()
EXPECTED_BRANCH = "review/knowledge-management-phase-2"
GIT = r"C:\Program Files\Git\cmd\git.exe"

ADMIN_API = ROOT / "frontend/src/lib/server/admin-api.ts"
VIEW = ROOT / "frontend/src/components/knowledge/knowledge-bases-view.tsx"
ACTIONS = ROOT / "frontend/src/components/knowledge/knowledge-document-actions.tsx"
ACTIONS_CSS = ROOT / "frontend/src/components/knowledge/knowledge-document-actions.module.css"

ALLOWED = {
    "apply_frontend_knowledge_mvp_ui.py",
    "apply_frontend_knowledge_mvp_ui_v2.py",
    "frontend/src/app/api/knowledge-bases/[tenantId]/[knowledgeBaseId]/documents/route.ts",
    "frontend/src/app/api/knowledge-bases/[tenantId]/[knowledgeBaseId]/documents/[documentId]/replace/route.ts",
    "frontend/src/lib/knowledge/contracts.ts",
    "frontend/src/lib/server/admin-api.ts",
    "frontend/src/components/knowledge/knowledge-bases-view.tsx",
    "frontend/src/components/knowledge/knowledge-document-actions.tsx",
    "frontend/src/components/knowledge/knowledge-document-actions.module.css",
}


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


def read_lf(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def write_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        text.rstrip("\n") + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("WROTE=" + path.relative_to(ROOT).as_posix())


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

status_lines = subprocess.run(
    [
        GIT,
        "status",
        "--short",
        "--untracked-files=all",
    ],
    cwd=ROOT,
    text=True,
    encoding="utf-8",
    capture_output=True,
    check=True,
).stdout.splitlines()

unexpected: list[str] = []
for line in status_lines:
    path = line[3:].strip().replace("\\", "/")
    if path not in ALLOWED:
        unexpected.append(line)

if unexpected:
    raise SystemExit(
        "Unexpected working-tree changes:\n"
        + "\n".join(unexpected)
    )

admin_api = read_lf(ADMIN_API)

old_content_type = '''  if (init.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
'''

new_content_type = '''  const isFormDataBody =
    typeof FormData !== "undefined" &&
    init.body instanceof FormData;

  if (
    init.body !== undefined &&
    !isFormDataBody &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }
'''

if "const isFormDataBody =" not in admin_api:
    admin_api = replace_once(
        admin_api,
        old_content_type,
        new_content_type,
        "admin-api-preserve-multipart-boundary",
    )

write_lf(ADMIN_API, admin_api)

actions_source = r'''"use client";

import {
  AlertTriangle,
  CheckCircle2,
  LoaderCircle,
  RefreshCw,
  Upload,
} from "lucide-react";

import {
  type ChangeEvent,
  type FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";

import type {
  KnowledgeDocumentJobRecord,
} from "@/lib/knowledge/contracts";

import styles from "./knowledge-document-actions.module.css";

type UploadActionsProps = {
  tenantId: string;
  knowledgeBaseId: string;
  assignedAgentIds: string[];
  onQueued: () => void;
};

type ReplaceActionProps = {
  tenantId: string;
  knowledgeBaseId: string;
  documentId: string;
  onQueued: () => void;
};

const copy = {
  title:
    "\u0631\u0641\u0639 \u0645\u0633\u062a\u0646\u062f \u062c\u062f\u064a\u062f",
  description:
    "\u0627\u062e\u062a\u0631 \u0648\u0643\u064a\u0644\u0627\u064b \u0645\u0631\u062a\u0628\u0637\u0627\u064b \u0628\u0642\u0627\u0639\u062f\u0629 \u0627\u0644\u0645\u0639\u0631\u0641\u0629\u060c \u062b\u0645 \u0627\u0631\u0641\u0639 \u0627\u0644\u0645\u0644\u0641 \u0644\u0645\u0639\u0627\u0644\u062c\u062a\u0647 \u0641\u064a \u0627\u0644\u062e\u0644\u0641\u064a\u0629.",
  chooseAgent:
    "\u0627\u062e\u062a\u0631 \u0627\u0644\u0648\u0643\u064a\u0644",
  sourceName:
    "\u0627\u0633\u0645 \u0627\u0644\u0645\u0635\u062f\u0631",
  chooseFile:
    "\u0627\u062e\u062a\u0631 \u0645\u0644\u0641\u0627\u064b",
  upload:
    "\u0631\u0641\u0639 \u0648\u0628\u062f\u0621 \u0627\u0644\u0645\u0639\u0627\u0644\u062c\u0629",
  uploading:
    "\u062c\u0627\u0631\u064a \u0625\u0631\u0633\u0627\u0644 \u0627\u0644\u0645\u0644\u0641",
  queued:
    "\u062a\u0645\u062a \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0645\u0644\u0641 \u0625\u0644\u0649 \u0637\u0627\u0628\u0648\u0631 \u0627\u0644\u0645\u0639\u0627\u0644\u062c\u0629.",
  uploadFailed:
    "\u062a\u0639\u0630\u0631 \u0631\u0641\u0639 \u0627\u0644\u0645\u0644\u0641.",
  noAssignedAgents:
    "\u0627\u0631\u0628\u0637 \u0648\u0643\u064a\u0644\u0627\u064b \u0628\u0642\u0627\u0639\u062f\u0629 \u0627\u0644\u0645\u0639\u0631\u0641\u0629 \u0642\u0628\u0644 \u0631\u0641\u0639 \u0627\u0644\u0645\u0633\u062a\u0646\u062f.",
  replace:
    "\u0627\u0633\u062a\u0628\u062f\u0627\u0644 \u0627\u0644\u0645\u0644\u0641",
  replacing:
    "\u062c\u0627\u0631\u064a \u0627\u0644\u0627\u0633\u062a\u0628\u062f\u0627\u0644",
  replaced:
    "\u062a\u0645\u062a \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0627\u0633\u062a\u0628\u062f\u0627\u0644 \u0625\u0644\u0649 \u0637\u0627\u0628\u0648\u0631 \u0627\u0644\u0645\u0639\u0627\u0644\u062c\u0629.",
  replacementFailed:
    "\u062a\u0639\u0630\u0631 \u0627\u0633\u062a\u0628\u062f\u0627\u0644 \u0627\u0644\u0645\u0644\u0641.",
} as const;

function readErrorDetail(
  payload: unknown,
  fallback: string,
): string {
  if (
    payload !== null &&
    typeof payload === "object" &&
    !Array.isArray(payload)
  ) {
    const detail = (
      payload as {
        detail?: unknown;
      }
    ).detail;

    if (typeof detail === "string") {
      return detail;
    }
  }

  return fallback;
}

async function postFormData(
  path: string,
  formData: FormData,
): Promise<KnowledgeDocumentJobRecord> {
  const response = await fetch(
    path,
    {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
      body: formData,
    },
  );

  if (response.status === 401) {
    window.location.assign(
      "/?next=%2Fdashboard%2Fknowledge-bases",
    );

    throw new Error(
      "Admin session is not active.",
    );
  }

  const payload = await response
    .json()
    .catch(() => null) as unknown;

  if (!response.ok) {
    throw new Error(
      readErrorDetail(
        payload,
        `Request failed: ${response.status}`,
      ),
    );
  }

  return payload as KnowledgeDocumentJobRecord;
}

export function KnowledgeDocumentActions({
  tenantId,
  knowledgeBaseId,
  assignedAgentIds,
  onQueued,
}: UploadActionsProps) {
  const fileInputRef =
    useRef<HTMLInputElement | null>(null);

  const [agentId, setAgentId] =
    useState(assignedAgentIds[0] ?? "");

  const [sourceName, setSourceName] =
    useState("admin-upload");

  const [file, setFile] =
    useState<File | null>(null);

  const [isSubmitting, setIsSubmitting] =
    useState(false);

  const [success, setSuccess] =
    useState<string | null>(null);

  const [error, setError] =
    useState<string | null>(null);

  useEffect(() => {
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

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (!agentId || file === null) {
      setError(copy.uploadFailed);
      return;
    }

    const formData = new FormData();
    formData.append("agent_id", agentId);
    formData.append(
      "source_name",
      sourceName.trim() || "admin-upload",
    );
    formData.append("file", file);

    setIsSubmitting(true);
    setSuccess(null);
    setError(null);

    try {
      await postFormData(
        `/api/knowledge-bases/${
          encodeURIComponent(tenantId)
        }/${
          encodeURIComponent(knowledgeBaseId)
        }/documents`,
        formData,
      );

      setFile(null);
      setSuccess(copy.queued);

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      onQueued();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : copy.uploadFailed,
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const noAssignedAgents =
    assignedAgentIds.length === 0;

  return (
    <section className={styles.section}>
      <div className={styles.heading}>
        <span className={styles.headingIcon}>
          <Upload aria-hidden="true" />
        </span>

        <div>
          <h4>{copy.title}</h4>
          <p>
            {noAssignedAgents
              ? copy.noAssignedAgents
              : copy.description}
          </p>
        </div>
      </div>

      <form
        className={styles.form}
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
      >
        <label className={styles.field}>
          <span>{copy.chooseAgent}</span>

          <select
            value={agentId}
            disabled={
              isSubmitting ||
              noAssignedAgents
            }
            onChange={(event) => {
              setAgentId(event.target.value);
            }}
          >
            <option value="">
              {copy.chooseAgent}
            </option>

            {assignedAgentIds.map(
              (assignedAgentId) => (
                <option
                  key={assignedAgentId}
                  value={assignedAgentId}
                >
                  {assignedAgentId}
                </option>
              ),
            )}
          </select>
        </label>

        <label className={styles.field}>
          <span>{copy.sourceName}</span>

          <input
            type="text"
            value={sourceName}
            maxLength={512}
            disabled={isSubmitting}
            onChange={(event) => {
              setSourceName(event.target.value);
            }}
          />
        </label>

        <label className={styles.fileField}>
          <span>
            {file?.name ?? copy.chooseFile}
          </span>

          <input
            ref={fileInputRef}
            type="file"
            disabled={isSubmitting}
            onChange={(
              event: ChangeEvent<HTMLInputElement>,
            ) => {
              setFile(
                event.target.files?.[0] ??
                null,
              );
            }}
          />
        </label>

        <button
          className={styles.primaryButton}
          type="submit"
          disabled={
            isSubmitting ||
            noAssignedAgents ||
            !agentId ||
            file === null
          }
        >
          {isSubmitting ? (
            <LoaderCircle
              className={styles.spinner}
              aria-hidden="true"
            />
          ) : (
            <Upload aria-hidden="true" />
          )}

          {isSubmitting
            ? copy.uploading
            : copy.upload}
        </button>
      </form>

      {success && (
        <div
          className={styles.success}
          role="status"
        >
          <CheckCircle2 aria-hidden="true" />
          <span>{success}</span>
        </div>
      )}

      {error && (
        <div
          className={styles.error}
          role="alert"
        >
          <AlertTriangle aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
    </section>
  );
}

export function KnowledgeDocumentReplaceAction({
  tenantId,
  knowledgeBaseId,
  documentId,
  onQueued,
}: ReplaceActionProps) {
  const [isSubmitting, setIsSubmitting] =
    useState(false);

  const [success, setSuccess] =
    useState<string | null>(null);

  const [error, setError] =
    useState<string | null>(null);

  async function handleFile(
    event: ChangeEvent<HTMLInputElement>,
  ): Promise<void> {
    const file =
      event.target.files?.[0] ?? null;

    event.target.value = "";

    if (file === null) {
      return;
    }

    const formData = new FormData();
    formData.append(
      "source_name",
      "admin-replacement",
    );
    formData.append("file", file);

    setIsSubmitting(true);
    setSuccess(null);
    setError(null);

    try {
      await postFormData(
        `/api/knowledge-bases/${
          encodeURIComponent(tenantId)
        }/${
          encodeURIComponent(knowledgeBaseId)
        }/documents/${
          encodeURIComponent(documentId)
        }/replace`,
        formData,
      );

      setSuccess(copy.replaced);
      onQueued();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : copy.replacementFailed,
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.replaceArea}>
      <label
        className={
          isSubmitting
            ? `${styles.replaceButton} ${styles.disabled}`
            : styles.replaceButton
        }
      >
        {isSubmitting ? (
          <LoaderCircle
            className={styles.spinner}
            aria-hidden="true"
          />
        ) : (
          <RefreshCw aria-hidden="true" />
        )}

        <span>
          {isSubmitting
            ? copy.replacing
            : copy.replace}
        </span>

        <input
          type="file"
          disabled={isSubmitting}
          onChange={(event) => {
            void handleFile(event);
          }}
        />
      </label>

      {success && (
        <span
          className={styles.inlineSuccess}
          role="status"
        >
          {success}
        </span>
      )}

      {error && (
        <span
          className={styles.inlineError}
          role="alert"
        >
          {error}
        </span>
      )}
    </div>
  );
}
'''

actions_css_source = r'''.section {
  border-bottom: 1px solid rgba(126, 117, 151, 0.14);
  padding: 20px 22px;
  background: rgba(22, 18, 39, 0.5);
}

.heading {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.headingIcon {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid rgba(151, 116, 255, 0.28);
  border-radius: 12px;
  background: rgba(84, 50, 158, 0.26);
  color: #b798ff;
}

.headingIcon svg {
  width: 19px;
  height: 19px;
}

.heading h4,
.heading p {
  margin: 0;
}

.heading h4 {
  font-size: 0.9rem;
}

.heading p {
  margin-top: 5px;
  color: #8e879b;
  font-size: 0.76rem;
  line-height: 1.7;
}

.form {
  display: grid;
  grid-template-columns:
    minmax(180px, 0.8fr)
    minmax(180px, 0.8fr)
    minmax(220px, 1.2fr)
    auto;
  gap: 11px;
  align-items: end;
  margin-top: 16px;
}

.field,
.fileField {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 7px;
}

.field > span,
.fileField > span {
  color: #9a94a7;
  font-size: 0.72rem;
  font-weight: 800;
}

.field select,
.field input,
.fileField {
  min-height: 44px;
  border: 1px solid rgba(137, 126, 164, 0.22);
  border-radius: 12px;
  background: rgba(13, 13, 27, 0.88);
  color: #f5f2ff;
  font: inherit;
}

.field select,
.field input {
  width: 100%;
  padding: 0 12px;
  outline: none;
}

.fileField {
  position: relative;
  justify-content: center;
  overflow: hidden;
  padding: 0 12px;
  cursor: pointer;
}

.fileField > span {
  overflow: hidden;
  color: #b7b0c4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fileField input,
.replaceButton input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.primaryButton,
.replaceButton {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid rgba(151, 116, 255, 0.38);
  border-radius: 12px;
  color: #ffffff;
  font: inherit;
  font-size: 0.76rem;
  font-weight: 900;
  cursor: pointer;
}

.primaryButton {
  min-height: 44px;
  padding: 0 16px;
  background: linear-gradient(
    135deg,
    rgba(116, 74, 220, 0.88),
    rgba(74, 43, 149, 0.88)
  );
}

.primaryButton:disabled,
.disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.primaryButton svg,
.replaceButton svg {
  width: 16px;
  height: 16px;
}

.success,
.error {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 13px;
  border-radius: 11px;
  padding: 10px 12px;
  font-size: 0.75rem;
}

.success {
  border: 1px solid rgba(46, 211, 180, 0.2);
  background: rgba(18, 75, 69, 0.22);
  color: #84e5d3;
}

.error {
  border: 1px solid rgba(255, 91, 120, 0.17);
  background: rgba(127, 26, 50, 0.12);
  color: #ff8ba0;
}

.success svg,
.error svg {
  width: 17px;
  height: 17px;
  flex: 0 0 auto;
}

.replaceArea {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 9px;
  margin-top: 14px;
}

.replaceButton {
  position: relative;
  min-height: 38px;
  padding: 0 13px;
  background: rgba(61, 39, 112, 0.55);
}

.inlineSuccess,
.inlineError {
  font-size: 0.7rem;
  line-height: 1.5;
}

.inlineSuccess {
  color: #75dfca;
}

.inlineError {
  color: #ff8ba0;
}

.spinner {
  animation: spin 0.85s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1180px) {
  .form {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .section {
    padding: 17px;
  }

  .form {
    grid-template-columns: minmax(0, 1fr);
  }

  .primaryButton,
  .replaceButton {
    width: 100%;
  }
}
'''

if ACTIONS.exists():
    existing = read_lf(ACTIONS)
    if existing != actions_source:
        raise SystemExit(
            "Knowledge actions component exists with unexpected content."
        )
else:
    write_lf(ACTIONS, actions_source)

if ACTIONS_CSS.exists():
    existing_css = read_lf(ACTIONS_CSS)
    if existing_css != actions_css_source:
        raise SystemExit(
            "Knowledge actions stylesheet exists with unexpected content."
        )
else:
    write_lf(ACTIONS_CSS, actions_css_source)

view = read_lf(VIEW)

import_anchor = '''import type {
  TenantDirectoryItem,
  TenantDirectoryResponse,
} from "@/lib/tenants/contracts";
'''

actions_import = '''import {
  KnowledgeDocumentActions,
  KnowledgeDocumentReplaceAction,
} from "@/components/knowledge/knowledge-document-actions";

import type {
  TenantDirectoryItem,
  TenantDirectoryResponse,
} from "@/lib/tenants/contracts";
'''

if "KnowledgeDocumentActions," not in view:
    view = replace_once(
        view,
        import_anchor,
        actions_import,
        "knowledge-view-actions-import",
    )

state_anchor = '''  const [
    refreshVersion,
    setRefreshVersion,
  ] = useState(0);
'''

state_replacement = '''  const [
    refreshVersion,
    setRefreshVersion,
  ] = useState(0);

  const [
    detailRefreshVersion,
    setDetailRefreshVersion,
  ] = useState(0);
'''

if "detailRefreshVersion" not in view:
    view = replace_once(
        view,
        state_anchor,
        state_replacement,
        "knowledge-view-detail-refresh-state",
    )

dependency_anchor = '''  }, [
    refreshVersion,
    selectedBaseId,
    selectedTenantId,
  ]);
'''

dependency_replacement = '''  }, [
    detailRefreshVersion,
    refreshVersion,
    selectedBaseId,
    selectedTenantId,
  ]);
'''

if (
    "detailRefreshVersion,\n    refreshVersion,"
    not in view
):
    view = replace_once(
        view,
        dependency_anchor,
        dependency_replacement,
        "knowledge-view-detail-refresh-dependency",
    )

current_base_anchor = '''  const currentBase =
    detail ??
    bases.find(
      (item) =>
        item.id === selectedBaseId,
    ) ??
    null;

  const totals = useMemo(
'''

current_base_replacement = '''  const currentBase =
    detail ??
    bases.find(
      (item) =>
        item.id === selectedBaseId,
    ) ??
    null;

  const hasActiveJobs = jobs.some(
    (job) =>
      job.status === "pending" ||
      job.status === "processing",
  );

  useEffect(() => {
    if (!hasActiveJobs) {
      return;
    }

    const timer = window.setInterval(
      () => {
        setDetailRefreshVersion(
          (current) => current + 1,
        );
      },
      3000,
    );

    return () => {
      window.clearInterval(timer);
    };
  }, [hasActiveJobs]);

  const totals = useMemo(
'''

if "const hasActiveJobs = jobs.some(" not in view:
    view = replace_once(
        view,
        current_base_anchor,
        current_base_replacement,
        "knowledge-view-active-job-polling",
    )

tabs_anchor = '''              <div className={styles.tabs}>
'''

tabs_replacement = '''              <KnowledgeDocumentActions
                key={currentBase.id}
                tenantId={selectedTenantId}
                knowledgeBaseId={currentBase.id}
                assignedAgentIds={
                  currentBase.assigned_agent_ids ??
                  []
                }
                onQueued={() => {
                  setActiveTab("jobs");
                  setDetailRefreshVersion(
                    (current) => current + 1,
                  );
                }}
              />

              <div className={styles.tabs}>
'''

if "<KnowledgeDocumentActions" not in view:
    view = replace_once(
        view,
        tabs_anchor,
        tabs_replacement,
        "knowledge-view-upload-actions",
    )

failure_anchor = '''                          {document.failure_reason && (
'''

failure_replacement = '''                          <KnowledgeDocumentReplaceAction
                            tenantId={
                              selectedTenantId
                            }
                            knowledgeBaseId={
                              currentBase.id
                            }
                            documentId={
                              document.id
                            }
                            onQueued={() => {
                              setActiveTab("jobs");
                              setDetailRefreshVersion(
                                (current) =>
                                  current + 1,
                              );
                            }}
                          />

                          {document.failure_reason && (
'''

if "<KnowledgeDocumentReplaceAction" not in view:
    view = replace_once(
        view,
        failure_anchor,
        failure_replacement,
        "knowledge-view-replace-action",
    )

write_lf(VIEW, view)

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
print(f"FRONTEND_KNOWLEDGE_UI_V2_LINT_EXIT={lint.returncode}")
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
print(f"FRONTEND_KNOWLEDGE_UI_V2_TSC_EXIT={tsc.returncode}")
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
print(f"FRONTEND_KNOWLEDGE_UI_V2_DRIFT_EXIT={drift.returncode}")
if drift.returncode != 0:
    raise SystemExit(drift.returncode)

print("\n=== DIFF CHECK ===")
diff = run(
    [GIT, "diff", "--check"],
    check=False,
)
print(f"FRONTEND_KNOWLEDGE_UI_V2_DIFF_EXIT={diff.returncode}")
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

print("FRONTEND_KNOWLEDGE_UI_V2_IMPLEMENTATION=PASSED")
print("MULTIPART_BOUNDARY_FIX=PASSED")
print("PRODUCTION_BUILD_RUN=False")
print("VISUAL_ACCEPTANCE_RUN=False")
print("FILES_STAGED=False")
print("FILES_COMMITTED=False")
