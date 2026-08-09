"use client";

import { useState } from "react";
import { LoaderCircle, X } from "lucide-react";

type Props = {
  open: boolean;
  title: string;
  description: string;
  label: string;
  placeholder: string;
  confirmText: string;
  confirmVariant?: "danger" | "warning" | "primary";
  loading: boolean;
  onConfirm: (text: string) => void;
  onClose: () => void;
};

export function ApplicationActionDialog({
  open,
  title,
  description,
  label,
  placeholder,
  confirmText,
  confirmVariant = "primary",
  loading,
  onConfirm,
  onClose,
}: Props) {
  const [value, setValue] = useState("");

  if (!open) return null;

  function handleClose() {
    setValue("");
    onClose();
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onConfirm(value);
  }

  const btnClass =
    confirmVariant === "danger"
      ? "btn btn--danger"
      : confirmVariant === "warning"
      ? "btn btn--warning"
      : "btn btn--primary";

  return (
    <div className="action-dialog-overlay" role="dialog" aria-modal="true">
      <div className="action-dialog-card">
        <div className="action-dialog-card__header">
          <h3>{title}</h3>
          <button
            type="button"
            className="action-dialog-card__close"
            onClick={handleClose}
            aria-label="إغلاق"
            disabled={loading}
          >
            <X aria-hidden="true" />
          </button>
        </div>

        <p className="action-dialog-card__desc">{description}</p>

        <form onSubmit={handleSubmit} className="action-dialog-card__form">
          <label htmlFor="dialog-text-input">{label}</label>
          <textarea
            id="dialog-text-input"
            rows={4}
            placeholder={placeholder}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={loading}
            required
          />

          <div className="action-dialog-card__actions">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={handleClose}
              disabled={loading}
            >
              إلغاء
            </button>
            <button
              type="submit"
              className={btnClass}
              disabled={loading || !value.trim()}
            >
              {loading ? (
                <LoaderCircle className="spinner" aria-hidden="true" />
              ) : (
                confirmText
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
