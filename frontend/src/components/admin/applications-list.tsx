"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  Clock,
  Filter,
  LoaderCircle,
  RefreshCw,
  Search,
  XCircle,
} from "lucide-react";

import type {
  ApplicationStatus,
  TenantApplication,
} from "@/lib/server/tenant-applications-api";

type FetchState =
  | { phase: "loading" }
  | { phase: "error"; message: string }
  | { phase: "ready"; applications: TenantApplication[] };

const statusLabels: Record<ApplicationStatus, string> = {
  email_pending: "انتظار البريد",
  under_review: "قيد المراجعة",
  changes_requested: "مطلوب تعديل",
  approved: "مقبول",
  rejected: "مرفوض",
};

const statusClasses: Record<ApplicationStatus, string> = {
  email_pending: "status-badge--pending",
  under_review: "status-badge--review",
  changes_requested: "status-badge--changes",
  approved: "status-badge--approved",
  rejected: "status-badge--rejected",
};

export function ApplicationsList() {
  const [state, setState] = useState<FetchState>({ phase: "loading" });
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");

  const loadApplications = useCallback(async (isRetry = false) => {
    if (isRetry) {
      setState({ phase: "loading" });
    }

    try {
      const response = await fetch("/api/admin/applications", {
        credentials: "same-origin",
        cache: "no-store",
        headers: { Accept: "application/json" },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const applications = (await response.json()) as TenantApplication[];
      setState({ phase: "ready", applications });
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "تعذر الاتصال بالخادم";
      setState({ phase: "error", message });
    }
  }, []);

  useEffect(() => {
    let ignore = false;

    async function doFetch() {
      try {
        const response = await fetch("/api/admin/applications", {
          credentials: "same-origin",
          cache: "no-store",
          headers: { Accept: "application/json" },
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const applications = (await response.json()) as TenantApplication[];
        if (!ignore) {
          setState({ phase: "ready", applications });
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
  }, []);

  const filteredApplications = useMemo(() => {
    if (state.phase !== "ready") return [];

    return state.applications.filter((app) => {
      const matchesSearch =
        searchQuery.trim() === "" ||
        app.applicant_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        app.email.toLowerCase().includes(searchQuery.toLowerCase());

      const matchesStatus =
        selectedStatus === "all" || app.status === selectedStatus;

      return matchesSearch && matchesStatus;
    });
  }, [state, searchQuery, selectedStatus]);

  if (state.phase === "loading") {
    return (
      <div className="applications-state" aria-live="polite" aria-busy="true">
        <LoaderCircle className="applications-state__spinner" aria-hidden="true" />
        <p>جاري تحميل طلبات الاشتراك…</p>
      </div>
    );
  }

  if (state.phase === "error") {
    return (
      <div className="applications-state is-error" role="alert">
        <AlertCircle aria-hidden="true" />
        <h3>تعذر تحميل الطلبات</h3>
        <p>{state.message}</p>
        <button
          type="button"
          className="btn btn--secondary"
          onClick={() => void loadApplications(true)}
        >
          <RefreshCw aria-hidden="true" />
          إعادة المحاولة
        </button>
      </div>
    );
  }

  return (
    <div className="applications-list-container">
      {/* Controls: Search & Filter */}
      <div className="applications-controls">
        <div className="applications-controls__search">
          <Search aria-hidden="true" />
          <input
            type="text"
            placeholder="البحث باسم مقدم الطلب، الشركة، أو البريد…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="applications-controls__filter">
          <Filter aria-hidden="true" />
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            aria-label="تصفية حسب الحالة"
          >
            <option value="all">جميع الحالات</option>
            <option value="under_review">قيد المراجعة</option>
            <option value="changes_requested">مطلوب تعديل</option>
            <option value="email_pending">انتظار البريد</option>
            <option value="approved">مقبول</option>
            <option value="rejected">مرفوض</option>
          </select>
        </div>

        <button
          type="button"
          className="btn btn--ghost btn--icon"
          onClick={() => void loadApplications(true)}
          title="تحديث البيانات"
        >
          <RefreshCw aria-hidden="true" />
        </button>
      </div>

      {/* Applications Table */}
      {filteredApplications.length === 0 ? (
        <div className="applications-empty">
          <Clock aria-hidden="true" />
          <p>لا توجد طلبات اشتراك تطابق الاختيار الحقيقي.</p>
        </div>
      ) : (
        <div className="applications-table-wrapper">
          <table className="applications-table">
            <thead>
              <tr>
                <th>مقدم الطلب</th>
                <th>اسم المنشأة</th>
                <th>الخطة</th>
                <th>البريد الإلكتروني</th>
                <th>الحالة</th>
                <th>تاريخ التقديم</th>
                <th>الإجراء</th>
              </tr>
            </thead>
            <tbody>
              {filteredApplications.map((app) => {
                const dateStr = new Date(app.submitted_at).toLocaleDateString(
                  "ar-SA",
                  {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  }
                );

                return (
                  <tr key={app.id}>
                    <td>
                      <strong className="app-applicant-name">
                        {app.applicant_name}
                      </strong>
                    </td>
                    <td>{app.company_name}</td>
                    <td>
                      <span className="app-plan-tag">{app.plan}</span>
                    </td>
                    <td>
                      <div className="app-email-cell">
                        <span>{app.email}</span>
                        {app.email_verified ? (
                          <span
                            className="email-badge email-badge--verified"
                            title="تم التحقق"
                          >
                            <CheckCircle2 aria-hidden="true" />
                          </span>
                        ) : (
                          <span
                            className="email-badge email-badge--unverified"
                            title="غير محقق"
                          >
                            <XCircle aria-hidden="true" />
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span
                        className={`status-badge ${statusClasses[app.status]}`}
                      >
                        {statusLabels[app.status]}
                      </span>
                    </td>
                    <td>
                      <span className="app-date">{dateStr}</span>
                    </td>
                    <td>
                      <Link
                        href={`/dashboard/applications/${app.id}`}
                        className="btn btn--sm btn--primary"
                      >
                        <span>التفاصيل</span>
                        <ChevronLeft aria-hidden="true" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
