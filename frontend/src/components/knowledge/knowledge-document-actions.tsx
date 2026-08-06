"use client";

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

  const effectiveAgentId =
    assignedAgentIds.includes(agentId)
      ? agentId
      : assignedAgentIds[0] ?? "";

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    if (!effectiveAgentId || file === null) {
      setError(copy.uploadFailed);
      return;
    }

    const formData = new FormData();
    formData.append(
      "agent_id",
      effectiveAgentId,
    );
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
            value={effectiveAgentId}
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
            !effectiveAgentId ||
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
