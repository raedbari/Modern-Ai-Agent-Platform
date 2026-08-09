"use client";

import {
  AlertCircle,
  CheckCircle,
  Clock,
  LoaderCircle,
  Mail,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

type ApplicationStatus =
  | "email_pending"
  | "under_review"
  | "changes_requested"
  | "approved"
  | "rejected";

type ApplicationStatusResponse = {
  status: ApplicationStatus;
  review_notes?: string;
  submitted_at: string;
};

type FetchState =
  | { phase: "loading" }
  | { phase: "error"; message: string }
  | { phase: "ready"; data: ApplicationStatusResponse };

async function fetchApplicationStatus(): Promise<ApplicationStatusResponse> {
  const response = await fetch("/api/saas/application/status", {
    credentials: "same-origin",
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (response.status === 401) {
    window.location.assign("/saas/login");
    // Return a never-resolving promise so the component stays in loading state
    // while the redirect is happening.
    return new Promise(() => undefined);
  }

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json() as Promise<ApplicationStatusResponse>;
}

function StatusIcon({ status }: { status: ApplicationStatus }) {
  switch (status) {
    case "email_pending":
      return (
        <div className="app-status-card__icon app-status-card__icon--pending">
          <Mail aria-hidden="true" />
        </div>
      );
    case "under_review":
      return (
        <div className="app-status-card__icon app-status-card__icon--review">
          <Clock aria-hidden="true" />
        </div>
      );
    case "changes_requested":
      return (
        <div className="app-status-card__icon app-status-card__icon--changes">
          <AlertCircle aria-hidden="true" />
        </div>
      );
    case "approved":
      return (
        <div className="app-status-card__icon app-status-card__icon--approved">
          <CheckCircle aria-hidden="true" />
        </div>
      );
    case "rejected":
      return (
        <div className="app-status-card__icon app-status-card__icon--rejected">
          <XCircle aria-hidden="true" />
        </div>
      );
  }
}

function StatusBody({ data }: { data: ApplicationStatusResponse }) {
  const { status, review_notes } = data;

  switch (status) {
    case "email_pending":
      return (
        <>
          <h2 className="app-status-card__title">
            في انتظار التحقق من البريد الإلكتروني
          </h2>
          <p className="app-status-card__description">
            يرجى التحقق من بريدك الإلكتروني والنقر على رابط التأكيد قبل
            المتابعة.
          </p>
          <Link className="app-status-card__action" href="/saas/verify-email">
            التحقق من البريد الإلكتروني
          </Link>
        </>
      );

    case "under_review":
      return (
        <>
          <h2 className="app-status-card__title">طلبك قيد المراجعة</h2>
          <p className="app-status-card__description">سنتواصل معك قريبًا</p>
        </>
      );

    case "changes_requested":
      return (
        <>
          <h2 className="app-status-card__title">مطلوب تعديلات</h2>
          {review_notes && (
            <div className="app-status-card__notes" role="note">
              {review_notes}
            </div>
          )}
          <p className="app-status-card__description">
            يرجى مراجعة الملاحظات أعلاه والتواصل معنا
          </p>
        </>
      );

    case "approved":
      return (
        <>
          <h2 className="app-status-card__title">تمت الموافقة على طلبك!</h2>
          <p className="app-status-card__description">
            تهانينا! يمكنك الآن الدخول إلى البوابة.
          </p>
          <Link className="app-status-card__action" href="/saas/login">
            الدخول إلى البوابة
          </Link>
        </>
      );

    case "rejected":
      return (
        <>
          <h2 className="app-status-card__title">تم رفض الطلب</h2>
          {review_notes && (
            <div className="app-status-card__notes" role="note">
              {review_notes}
            </div>
          )}
          <p className="app-status-card__description app-status-card__description--muted">
            لن يمكن تقديم طلب جديد
          </p>
        </>
      );
  }
}

export function ApplicationStatusCard() {
  const [state, setState] = useState<FetchState>({ phase: "loading" });

  function load() {
    setState({ phase: "loading" });

    fetchApplicationStatus()
      .then((data) => {
        setState({ phase: "ready", data });
      })
      .catch((error: unknown) => {
        const message =
          error instanceof Error
            ? error.message
            : "حدث خطأ غير متوقع";
        setState({ phase: "error", message });
      });
  }

  useEffect(() => {
    let ignore = false;

    fetchApplicationStatus()
      .then((data) => {
        if (!ignore) {
          setState({ phase: "ready", data });
        }
      })
      .catch((error: unknown) => {
        if (!ignore) {
          const message =
            error instanceof Error ? error.message : "حدث خطأ غير متوقع";
          setState({ phase: "error", message });
        }
      });

    return () => {
      ignore = true;
    };
  }, []);

  if (state.phase === "loading") {
    return (
      <div className="app-status-card" aria-live="polite" aria-busy="true">
        <div className="app-status-card__spinner">
          <LoaderCircle aria-hidden="true" />
        </div>
        <p className="app-status-card__loading-text">جاري التحميل…</p>
      </div>
    );
  }

  if (state.phase === "error") {
    return (
      <div className="app-status-card" role="alert">
        <div className="app-status-card__icon app-status-card__icon--error">
          <AlertCircle aria-hidden="true" />
        </div>
        <h2 className="app-status-card__title">حدث خطأ</h2>
        <p className="app-status-card__description">{state.message}</p>
        <button className="app-status-card__retry" type="button" onClick={load}>
          إعادة المحاولة
        </button>
      </div>
    );
  }

  return (
    <div className="app-status-card">
      <StatusIcon status={state.data.status} />
      <StatusBody data={state.data} />
    </div>
  );
}
