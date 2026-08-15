"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  FileEdit,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  User,
  XCircle,
} from "lucide-react";

import { ApplicationActionDialog } from "@/components/admin/application-action-dialog";
import type {
  ApplicationStatus,
  TenantApplication,
} from "@/lib/server/tenant-applications-api";

type Props = {
  applicationId: string;
};

type FetchState =
  | { phase: "loading" }
  | { phase: "error"; message: string }
  | { phase: "ready"; application: TenantApplication };

const statusLabels: Record<ApplicationStatus, string> = {
  email_pending: "انتظار التحقق من البريد",
  under_review: "قيد المراجعة",
  changes_requested: "مطلوب تعديلات",
  approved: "تمت الموافقة",
  rejected: "مرفوض",
};

const statusClasses: Record<ApplicationStatus, string> = {
  email_pending: "status-badge--pending",
  under_review: "status-badge--review",
  changes_requested: "status-badge--changes",
  approved: "status-badge--approved",
  rejected: "status-badge--rejected",
};

export function ApplicationDetail({ applicationId }: Props) {
  const [state, setState] = useState<FetchState>({ phase: "loading" });
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Dialog states
  const [dialogType, setDialogType] = useState<"reject" | "changes" | null>(null);

  const loadApplication = useCallback(
    async (isRetry = false) => {
      if (isRetry) {
        setState({ phase: "loading" });
      }
      try {
        const response = await fetch(
          `/api/admin/applications/${encodeURIComponent(applicationId)}`,
          {
            credentials: "same-origin",
            cache: "no-store",
            headers: { Accept: "application/json" },
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const application = (await response.json()) as TenantApplication;
        setState({ phase: "ready", application });
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "تعذر الاتصال بالخادم";
        setState({ phase: "error", message });
      }
    },
    [applicationId]
  );

  useEffect(() => {
    let ignore = false;

    async function doFetch() {
      try {
        const response = await fetch(
          `/api/admin/applications/${encodeURIComponent(applicationId)}`,
          {
            credentials: "same-origin",
            cache: "no-store",
            headers: { Accept: "application/json" },
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const application = (await response.json()) as TenantApplication;
        if (!ignore) {
          setState({ phase: "ready", application });
        }
      } catch (error) {
        if (!ignore) {
          const message =
            error instanceof Error ? error.message : "تعذر الاتصال بالخادم";
          setState({ phase: "error", message });
        }
      }
    }

    void doFetch();

    return () => {
      ignore = true;
    };
  }, [applicationId]);

  async function handleApprove() {
    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);

    try {
      const response = await fetch(
        `/api/admin/applications/${encodeURIComponent(applicationId)}/approve`,
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: { Accept: "application/json" },
        }
      );

      if (!response.ok) {
        const data = (await response.json()) as { detail?: string };
        throw new Error(data.detail || `HTTP ${response.status}`);
      }

      const updated = (await response.json()) as TenantApplication;
      setState({ phase: "ready", application: updated });
      setActionSuccess("تمت الموافقة على طلب الاشتراك بنجاح.");
    } catch (error) {
      const msg = error instanceof Error ? error.message : "حدث خطأ أثناء التنفيذ";
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleReject(reason: string) {
    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);

    try {
      const response = await fetch(
        `/api/admin/applications/${encodeURIComponent(applicationId)}/reject`,
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ reason }),
        }
      );

      if (!response.ok) {
        const data = (await response.json()) as { detail?: string };
        throw new Error(data.detail || `HTTP ${response.status}`);
      }

      const updated = (await response.json()) as TenantApplication;
      setState({ phase: "ready", application: updated });
      setActionSuccess("تم رفض طلب الاشتراك.");
      setDialogType(null);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "حدث خطأ أثناء التنفيذ";
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleRequestChanges(notes: string) {
    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);

    try {
      const response = await fetch(
        `/api/admin/applications/${encodeURIComponent(
          applicationId
        )}/request-changes`,
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ notes }),
        }
      );

      if (!response.ok) {
        const data = (await response.json()) as { detail?: string };
        throw new Error(data.detail || `HTTP ${response.status}`);
      }

      const updated = (await response.json()) as TenantApplication;
      setState({ phase: "ready", application: updated });
      setActionSuccess("تم طلب التعديلات من مقدم الطلب.");
      setDialogType(null);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "حدث خطأ أثناء التنفيذ";
      setActionError(msg);
    } finally {
      setActionLoading(false);
    }
  }

  if (state.phase === "loading") {
    return (
      <div className="applications-state" aria-live="polite" aria-busy="true">
        <LoaderCircle className="applications-state__spinner" aria-hidden="true" />
        <p>جاري تحميل تفاصيل الطلب…</p>
      </div>
    );
  }

  if (state.phase === "error") {
    return (
      <div className="applications-state is-error" role="alert">
        <AlertCircle aria-hidden="true" />
        <h3>تعذر تحميل تفاصيل الطلب</h3>
        <p>{state.message}</p>
        <div className="applications-state__actions">
          <Link href="/dashboard/applications" className="btn btn--ghost">
            <ArrowRight aria-hidden="true" />
            العودة للطلبات
          </Link>
          <button
            type="button"
            className="btn btn--secondary"
            onClick={() => void loadApplication()}
          >
            <RefreshCw aria-hidden="true" />
            إعادة المحاولة
          </button>
        </div>
      </div>
    );
  }

  const app = state.application;
  const isPendingReview =
    app.status === "under_review" || app.status === "changes_requested";

  return (
    <div className="application-detail-container">
      {/* Top back navigation & status header */}
      <div className="application-detail-header">
        <Link href="/dashboard/applications" className="btn btn--ghost btn--sm">
          <ArrowRight aria-hidden="true" />
          <span>العودة لجميع الطلبات</span>
        </Link>

        <div className="application-detail-header__status">
          <span className={`status-badge ${statusClasses[app.status]}`}>
            {statusLabels[app.status]}
          </span>
        </div>
      </div>

      {/* Alert banners */}
      {actionError && (
        <div className="app-alert app-alert--error" role="alert">
          <AlertCircle aria-hidden="true" />
          <span>{actionError}</span>
        </div>
      )}

      {actionSuccess && (
        <div className="app-alert app-alert--success" role="status">
          <CheckCircle2 aria-hidden="true" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Application Details Grid */}
      <div className="application-detail-grid">
        {/* Card 1: Applicant Information */}
        <div className="app-detail-card">
          <div className="app-detail-card__header">
            <User aria-hidden="true" />
            <h3>بيانات مقدم الطلب والمنشأة</h3>
          </div>
          <div className="app-detail-card__body">
            <div className="detail-row">
              <span className="detail-label">الاسم الكامل</span>
              <strong className="detail-value">{app.applicant_name}</strong>
            </div>

            <div className="detail-row">
              <span className="detail-label">البريد الإلكتروني</span>
              <div className="detail-value app-email-cell">
                <span>{app.email}</span>
                {app.email_verified ? (
                  <span className="email-badge email-badge--verified">
                    <CheckCircle2 aria-hidden="true" /> محقق
                  </span>
                ) : (
                  <span className="email-badge email-badge--unverified">
                    <XCircle aria-hidden="true" /> غير محقق
                  </span>
                )}
              </div>
            </div>

            <div className="detail-row">
              <span className="detail-label">اسم المنشأة</span>
              <strong className="detail-value">{app.company_name}</strong>
            </div>

            <div className="detail-row">
              <span className="detail-label">الخطة المطلوبة</span>
              <span className="app-plan-tag">{app.plan}</span>
            </div>
          </div>
        </div>

        {/* Card 2: Timeline & Audit */}
        <div className="app-detail-card">
          <div className="app-detail-card__header">
            <Clock aria-hidden="true" />
            <h3>التاريخ وسجل المراجعة</h3>
          </div>
          <div className="app-detail-card__body">
            <div className="detail-row">
              <span className="detail-label">تاريخ تقديم الطلب</span>
              <span className="detail-value">
                {new Date(app.submitted_at).toLocaleString("ar-SA")}
              </span>
            </div>

            {app.reviewed_at && (
              <div className="detail-row">
                <span className="detail-label">تاريخ المراجعة</span>
                <span className="detail-value">
                  {new Date(app.reviewed_at).toLocaleString("ar-SA")}
                </span>
              </div>
            )}

            {app.reviewed_by && (
              <div className="detail-row">
                <span className="detail-label">تمت المراجعة بواسطة</span>
                <span className="detail-value">{app.reviewed_by}</span>
              </div>
            )}

            {app.review_notes && (
              <div className="detail-row detail-row--full">
                <span className="detail-label">ملاحظات المراجعة</span>
                <div className="detail-notes-box">{app.review_notes}</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Review Actions Footer Bar */}
      <div className="application-actions-bar">
        <div className="application-actions-bar__info">
          <span>إجراءات القرار على الطلب</span>
        </div>

        <div className="application-actions-bar__buttons">
          <button
            type="button"
            className="btn btn--danger"
            disabled={actionLoading || app.status === "rejected"}
            onClick={() => setDialogType("reject")}
          >
            <XCircle aria-hidden="true" />
            <span>رفض الطلب</span>
          </button>

          <button
            type="button"
            className="btn btn--warning"
            disabled={actionLoading || !isPendingReview}
            onClick={() => setDialogType("changes")}
          >
            <FileEdit aria-hidden="true" />
            <span>طلب تعديلات</span>
          </button>

          <button
            type="button"
            className="btn btn--success"
            disabled={actionLoading || app.status === "approved"}
            onClick={() => void handleApprove()}
          >
            {actionLoading ? (
              <LoaderCircle className="spinner" aria-hidden="true" />
            ) : (
              <ShieldCheck aria-hidden="true" />
            )}
            <span>الموافقة وتفعيل الحساب</span>
          </button>
        </div>
      </div>

      {/* Rejection Dialog */}
      <ApplicationActionDialog
        open={dialogType === "reject"}
        title="رفض طلب الاشتراك"
        description="يرجى كتابة سبب رفض الطلب. سيظهر هذا السبب لمقدم الطلب."
        label="سبب الرفض"
        placeholder="مثال: البيانات المدخلة غير مستوفية للشروط..."
        confirmText="تأكيد الرفض"
        confirmVariant="danger"
        loading={actionLoading}
        onConfirm={(reason) => void handleReject(reason)}
        onClose={() => setDialogType(null)}
      />

      {/* Request Changes Dialog */}
      <ApplicationActionDialog
        open={dialogType === "changes"}
        title="طلب تعديلات على الطلب"
        description="ادخل الملاحظات أو التعديلات المطلوبة من المنشأة."
        label="التعديلات المطلوبة"
        placeholder="مثال: يرجى تعديل اسم المنشأة الرسمي والتحقق من البريد..."
        confirmText="إرسال طلب التعديل"
        confirmVariant="warning"
        loading={actionLoading}
        onConfirm={(notes) => void handleRequestChanges(notes)}
        onClose={() => setDialogType(null)}
      />
    </div>
  );
}
