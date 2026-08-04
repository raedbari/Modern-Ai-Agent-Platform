"use client";

import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Bot,
  CheckCircle2,
  KeyRound,
  Clock3,
  RefreshCw,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useState,
} from "react";

import type {
  DashboardAuditEvent,
  DashboardOverview,
} from "@/lib/dashboard/overview";

const copy = {
  eyebrow:
    "\u0646\u0638\u0631\u0629 \u0639\u0627\u0645\u0629 \u0645\u0628\u0627\u0634\u0631\u0629",
  title:
    "\u0623\u062f\u0627\u0621 Athkachatbots",
  description:
    "\u0625\u062d\u0635\u0627\u0621\u0627\u062a \u062d\u0642\u064a\u0642\u064a\u0629 \u0645\u062c\u0645\u0639\u0629 \u0645\u0646 \u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u0639\u0645\u0644\u0627\u0621 \u0648\u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0648\u0633\u062c\u0644 \u0627\u0644\u0625\u062f\u0627\u0631\u0629.",
  tenants:
    "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0639\u0645\u0644\u0627\u0621",
  agents:
    "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  activeAgents:
    "\u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0627\u0644\u0646\u0634\u0637\u0648\u0646",
  activeKeys:
    "\u0645\u0641\u0627\u062a\u064a\u062d API \u0627\u0644\u0646\u0634\u0637\u0629",
  active:
    "\u0646\u0634\u0637",
  inactive:
    "\u0645\u0648\u0642\u0641",
  recentActivity:
    "\u0622\u062e\u0631 \u0627\u0644\u0623\u0646\u0634\u0637\u0629",
  recentActivityDescription:
    "\u0622\u062e\u0631 \u0627\u0644\u0623\u062d\u062f\u0627\u062b \u0627\u0644\u0645\u0633\u062c\u0644\u0629 \u0641\u064a \u0633\u062c\u0644 \u0627\u0644\u0625\u062f\u0627\u0631\u0629.",
  topTenants:
    "\u0627\u0644\u0639\u0645\u0644\u0627\u0621 \u062d\u0633\u0628 \u0639\u062f\u062f \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  topTenantsDescription:
    "\u062a\u0631\u062a\u064a\u0628 \u0645\u0628\u0646\u064a \u0639\u0644\u0649 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u062d\u0642\u064a\u0642\u064a\u0629.",
  platformStatus:
    "\u062d\u0627\u0644\u0629 \u0627\u0644\u0645\u0646\u0635\u0629",
  healthy:
    "\u062c\u0645\u064a\u0639 \u0645\u0635\u0627\u062f\u0631 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0645\u062a\u0627\u062d\u0629",
  partial:
    "\u062a\u0645 \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u062c\u0632\u0626\u064a\u064b\u0627",
  refresh:
    "\u062a\u062d\u062f\u064a\u062b",
  retry:
    "\u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629",
  loading:
    "\u062c\u0627\u0631\u064a \u062c\u0645\u0639 \u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u0645\u0646\u0635\u0629",
  error:
    "\u062a\u0639\u0630\u0631 \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u0646\u0638\u0631\u0629 \u0627\u0644\u0639\u0627\u0645\u0629.",
  noActivity:
    "\u0644\u0627 \u062a\u0648\u062c\u062f \u0623\u0646\u0634\u0637\u0629 \u0625\u062f\u0627\u0631\u064a\u0629 \u062d\u062f\u064a\u062b\u0629.",
  noTenants:
    "\u0644\u0627 \u064a\u0648\u062c\u062f \u0639\u0645\u0644\u0627\u0621 \u062d\u0627\u0644\u064a\u064b\u0627.",
  agentsLabel:
    "\u0648\u0643\u064a\u0644",
  keysLabel:
    "\u0645\u0641\u062a\u0627\u062d \u0646\u0634\u0637",
  openTenants:
    "\u0641\u062a\u062d \u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0639\u0645\u0644\u0627\u0621",
  updated:
    "\u0622\u062e\u0631 \u062a\u062d\u062f\u064a\u062b",
} as const;

const eventLabels: Record<string, string> = {
  login_success:
    "\u062a\u0633\u062c\u064a\u0644 \u062f\u062e\u0648\u0644 \u0646\u0627\u062c\u062d",
  login_failure:
    "\u0645\u062d\u0627\u0648\u0644\u0629 \u062f\u062e\u0648\u0644 \u0641\u0627\u0634\u0644\u0629",
  logout:
    "\u062a\u0633\u062c\u064a\u0644 \u062e\u0631\u0648\u062c",
  token_refreshed:
    "\u062a\u062c\u062f\u064a\u062f \u062c\u0644\u0633\u0629",
  token_replay_detected:
    "\u0627\u0643\u062a\u0634\u0627\u0641 \u0625\u0639\u0627\u062f\u0629 \u0627\u0633\u062a\u062e\u062f\u0627\u0645 \u0631\u0645\u0632",
  password_changed:
    "\u062a\u063a\u064a\u064a\u0631 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631",
};

const numberFormatter =
  new Intl.NumberFormat("ar");

const dateFormatter =
  new Intl.DateTimeFormat(
    "ar",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  );

function eventLabel(
  event: DashboardAuditEvent,
): string {
  return (
    eventLabels[event.event_type] ??
    event.event_type.replaceAll("_", " ")
  );
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return dateFormatter.format(date);
}

export function DashboardOverviewView() {
  const [data, setData] =
    useState<DashboardOverview | null>(null);
  const [isLoading, setIsLoading] =
    useState(true);
  const [error, setError] =
    useState<string | null>(null);

  const requestOverview = useCallback(
    async (
      signal?: AbortSignal,
    ): Promise<DashboardOverview> => {
      const response = await fetch(
        "/api/dashboard/overview",
        {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          signal,
          headers: {
            Accept: "application/json",
          },
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard",
        );

        throw new Error(
          "Admin session is not active.",
        );
      }

      if (!response.ok) {
        throw new Error(
          `Overview failed: ${response.status}`,
        );
      }

      return (
        await response.json()
      ) as DashboardOverview;
    },
    [],
  );

  const loadOverview = useCallback(
    async () => {
      setIsLoading(true);
      setError(null);

      try {
        const payload =
          await requestOverview();

        setData(payload);
      } catch {
        setError(copy.error);
      } finally {
        setIsLoading(false);
      }
    },
    [requestOverview],
  );

  useEffect(() => {
    const controller =
      new AbortController();

    async function loadInitialOverview(): Promise<void> {
      try {
        const payload =
          await requestOverview(
            controller.signal,
          );

        if (!controller.signal.aborted) {
          setData(payload);
        }
      } catch {
        if (!controller.signal.aborted) {
          setError(copy.error);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadInitialOverview();

    return () => {
      controller.abort();
    };
  }, [requestOverview]);

  if (isLoading && data === null) {
    return (
      <main className="overview-live">
        <section className="overview-loading">
          <RefreshCw
            className="overview-loading__spinner"
            aria-hidden="true"
          />
          <h2>{copy.loading}</h2>

          <div className="overview-skeleton-grid">
            <span />
            <span />
            <span />
            <span />
          </div>
        </section>
      </main>
    );
  }

  if (error && data === null) {
    return (
      <main className="overview-live">
        <section className="overview-error">
          <AlertTriangle aria-hidden="true" />
          <h2>{copy.error}</h2>

          <button
            type="button"
            onClick={() => {
              void loadOverview();
            }}
          >
            <RefreshCw aria-hidden="true" />
            {copy.retry}
          </button>
        </section>
      </main>
    );
  }

  if (data === null) {
    return null;
  }

  const metrics = [
    {
      label: copy.tenants,
      value: data.tenants.total,
      detail:
        `${numberFormatter.format(data.tenants.active)} ${copy.active}`,
      icon: UsersRound,
    },
    {
      label: copy.agents,
      value: data.agents.total,
      detail:
        `${numberFormatter.format(data.agents.inactive)} ${copy.inactive}`,
      icon: Bot,
    },
    {
      label: copy.activeAgents,
      value: data.agents.active,
      detail:
        `${numberFormatter.format(data.agents.total)} ${copy.agentsLabel}`,
      icon: Activity,
    },
    {
      label: copy.activeKeys,
      value: data.api_keys.active,
      detail:
        `${numberFormatter.format(data.api_keys.revoked)} ${copy.inactive}`,
      icon: KeyRound,
    },
  ];

  return (
    <main className="overview-live">
      <section className="overview-live__hero">
        <div>
          <span className="overview-live__eyebrow">
            <Activity aria-hidden="true" />
            {copy.eyebrow}
          </span>

          <h2>{copy.title}</h2>
          <p>{copy.description}</p>
        </div>

        <button
          className="overview-refresh"
          type="button"
          disabled={isLoading}
          onClick={() => {
            void loadOverview();
          }}
        >
          <RefreshCw
            className={
              isLoading
                ? "is-spinning"
                : undefined
            }
            aria-hidden="true"
          />
          {copy.refresh}
        </button>
      </section>

      <section className="overview-metrics">
        {metrics.map((metric) => {
          const Icon = metric.icon;

          return (
            <article
              key={metric.label}
              className="overview-metric-card"
            >
              <span className="overview-metric-card__icon">
                <Icon aria-hidden="true" />
              </span>

              <div>
                <span>{metric.label}</span>
                <strong>
                  {numberFormatter.format(
                    metric.value,
                  )}
                </strong>
                <small>{metric.detail}</small>
              </div>
            </article>
          );
        })}
      </section>

      <section className="overview-content-grid">
        <article className="overview-panel overview-panel--activity">
          <header className="overview-panel__header">
            <div>
              <h3>{copy.recentActivity}</h3>
              <p>
                {copy.recentActivityDescription}
              </p>
            </div>

            <span className="overview-panel__count">
              {numberFormatter.format(
                data.audit.loaded,
              )}
            </span>
          </header>

          {data.audit.recent.length === 0 ? (
            <div className="overview-empty">
              <Clock3 aria-hidden="true" />
              <p>{copy.noActivity}</p>
            </div>
          ) : (
            <div className="overview-activity-list">
              {data.audit.recent.map(
                (event) => (
                  <div
                    key={event.id}
                    className="overview-activity-item"
                  >
                    <span
                      className={
                        event.outcome === "success"
                          ? "overview-activity-item__status is-success"
                          : "overview-activity-item__status is-failure"
                      }
                    >
                      {event.outcome === "success" ? (
                        <CheckCircle2
                          aria-hidden="true"
                        />
                      ) : (
                        <AlertTriangle
                          aria-hidden="true"
                        />
                      )}
                    </span>

                    <div>
                      <strong>
                        {eventLabel(event)}
                      </strong>
                      <small>
                        {formatDate(
                          event.created_at,
                        )}
                      </small>
                    </div>
                  </div>
                ),
              )}
            </div>
          )}
        </article>

        <div className="overview-side-column">
          <article className="overview-panel">
            <header className="overview-panel__header">
              <div>
                <h3>{copy.platformStatus}</h3>
                <p>
                  {data.status === "healthy"
                    ? copy.healthy
                    : copy.partial}
                </p>
              </div>
            </header>

            <div
              className={
                data.status === "healthy"
                  ? "overview-health is-healthy"
                  : "overview-health is-partial"
              }
            >
              {data.status === "healthy" ? (
                <ShieldCheck aria-hidden="true" />
              ) : (
                <AlertTriangle aria-hidden="true" />
              )}

              <div>
                <strong>
                  {data.status === "healthy"
                    ? copy.healthy
                    : copy.partial}
                </strong>

                <small>
                  {copy.updated}:{" "}
                  {formatDate(
                    data.generated_at,
                  )}
                </small>
              </div>
            </div>

            {data.warnings.length > 0 && (
              <div className="overview-warning">
                <AlertTriangle aria-hidden="true" />
                <span>
                  {numberFormatter.format(
                    data.warnings.length,
                  )}{" "}
                  \u0645\u0635\u062f\u0631 \u0628\u064a\u0627\u0646\u0627\u062a \u0644\u0645 \u064a\u0643\u062a\u0645\u0644 \u062a\u062d\u0645\u064a\u0644\u0647.
                </span>
              </div>
            )}
          </article>

          <article className="overview-panel">
            <header className="overview-panel__header">
              <div>
                <h3>{copy.topTenants}</h3>
                <p>
                  {copy.topTenantsDescription}
                </p>
              </div>
            </header>

            {data.top_tenants.length === 0 ? (
              <div className="overview-empty">
                <UsersRound aria-hidden="true" />
                <p>{copy.noTenants}</p>
              </div>
            ) : (
              <div className="overview-tenant-list">
                {data.top_tenants.map(
                  (tenant, index) => (
                    <div
                      key={tenant.id}
                      className="overview-tenant-item"
                    >
                      <span className="overview-tenant-item__rank">
                        {numberFormatter.format(
                          index + 1,
                        )}
                      </span>

                      <div>
                        <strong>
                          {tenant.name}
                        </strong>
                        <small>
                          {numberFormatter.format(
                            tenant.agents_total,
                          )}{" "}
                          {copy.agentsLabel}
                          {" ? "}
                          {numberFormatter.format(
                            tenant.api_keys_active,
                          )}{" "}
                          {copy.keysLabel}
                        </small>
                      </div>

                      <span
                        className={
                          tenant.is_active
                            ? "overview-tenant-item__state is-active"
                            : "overview-tenant-item__state"
                        }
                      />
                    </div>
                  ),
                )}
              </div>
            )}

            <Link
              className="overview-panel__link"
              href="/dashboard/tenants"
            >
              {copy.openTenants}
              <ArrowLeft aria-hidden="true" />
            </Link>
          </article>
        </div>
      </section>
    </main>
  );
}
