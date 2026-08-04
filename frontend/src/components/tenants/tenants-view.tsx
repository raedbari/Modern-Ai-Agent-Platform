"use client";

import {
  AlertTriangle,
  Bot,
  CalendarDays,
  CheckCircle2,
  KeyRound,
  LoaderCircle,
  Power,
  PowerOff,
  RefreshCw,
  Search,
  Trash2,
  UsersRound,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  TenantDirectoryItem,
  TenantDirectoryResponse,
} from "@/lib/tenants/contracts";

type StatusFilter =
  | "all"
  | "active"
  | "inactive";

type ErrorPayload = {
  detail?: unknown;
};

const copy = {
  eyebrow:
    "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0639\u0645\u0644\u0627\u0621",
  title:
    "\u062f\u0644\u064a\u0644 \u0627\u0644\u0639\u0645\u0644\u0627\u0621",
  description:
    "\u0627\u0633\u062a\u0639\u0631\u0636 \u0645\u0633\u0627\u062d\u0627\u062a \u0627\u0644\u0639\u0645\u0644\u0627\u0621 \u0648\u062d\u0627\u0644\u0629 \u0648\u0643\u0644\u0627\u0626\u0647\u0645 \u0648\u0645\u0641\u0627\u062a\u064a\u062d API \u0645\u0646 \u0648\u0627\u062c\u0647\u0629 \u0648\u0627\u062d\u062f\u0629.",
  total:
    "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0639\u0645\u0644\u0627\u0621",
  active:
    "\u0627\u0644\u0639\u0645\u0644\u0627\u0621 \u0627\u0644\u0646\u0634\u0637\u0648\u0646",
  agents:
    "\u0625\u062c\u0645\u0627\u0644\u064a \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  keys:
    "\u0645\u0641\u0627\u062a\u064a\u062d API \u0627\u0644\u0646\u0634\u0637\u0629",
  search:
    "\u0627\u0628\u062d\u062b \u0628\u0627\u0633\u0645 \u0627\u0644\u0639\u0645\u064a\u0644 \u0623\u0648 \u0627\u0644\u0645\u0639\u0631\u0641",
  all:
    "\u0627\u0644\u0643\u0644",
  activeFilter:
    "\u0646\u0634\u0637",
  inactiveFilter:
    "\u0645\u0648\u0642\u0641",
  client:
    "\u0627\u0644\u0639\u0645\u064a\u0644",
  status:
    "\u0627\u0644\u062d\u0627\u0644\u0629",
  agentsColumn:
    "\u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  keysColumn:
    "\u0645\u0641\u0627\u062a\u064a\u062d API",
  created:
    "\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0625\u0646\u0634\u0627\u0621",
  actions:
    "\u0627\u0644\u0625\u062c\u0631\u0627\u0621\u0627\u062a",
  activate:
    "\u062a\u0641\u0639\u064a\u0644",
  suspend:
    "\u062a\u0639\u0637\u064a\u0644",
  delete:
    "\u062d\u0630\u0641 \u0646\u0647\u0627\u0626\u064a",
  activeState:
    "\u0646\u0634\u0637",
  inactiveState:
    "\u0645\u0648\u0642\u0641",
  refresh:
    "\u062a\u062d\u062f\u064a\u062b",
  loading:
    "\u062c\u0627\u0631\u064a \u062a\u062d\u0645\u064a\u0644 \u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u0639\u0645\u0644\u0627\u0621",
  loadError:
    "\u062a\u0639\u0630\u0631 \u062a\u062d\u0645\u064a\u0644 \u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u0639\u0645\u0644\u0627\u0621.",
  retry:
    "\u0625\u0639\u0627\u062f\u0629 \u0627\u0644\u0645\u062d\u0627\u0648\u0644\u0629",
  empty:
    "\u0644\u0627 \u064a\u0648\u062c\u062f \u0639\u0645\u0644\u0627\u0621 \u064a\u0637\u0627\u0628\u0642\u0648\u0646 \u0627\u0644\u0628\u062d\u062b \u0648\u0627\u0644\u062a\u0635\u0641\u064a\u0629.",
  partial:
    "\u0628\u0639\u0636 \u0625\u062d\u0635\u0627\u0621\u0627\u062a \u0627\u0644\u0639\u0645\u0644\u0627\u0621 \u0644\u0645 \u064a\u0643\u062a\u0645\u0644 \u062a\u062d\u0645\u064a\u0644\u0647\u0627.",
  permissionDenied:
    "\u0644\u064a\u0633 \u0644\u062f\u064a\u0643 \u0627\u0644\u0635\u0644\u0627\u062d\u064a\u0629 \u0644\u062a\u0646\u0641\u064a\u0630 \u0647\u0630\u0627 \u0627\u0644\u0625\u062c\u0631\u0627\u0621.",
  conflict:
    "\u062a\u0639\u0630\u0631 \u062d\u0630\u0641 \u0627\u0644\u0639\u0645\u064a\u0644 \u0628\u0633\u0628\u0628 \u0648\u062c\u0648\u062f \u0645\u0648\u0627\u0631\u062f \u0645\u0631\u062a\u0628\u0637\u0629 \u0623\u0648 \u062a\u0639\u0627\u0631\u0636 \u0641\u064a \u062f\u0648\u0631\u0629 \u062d\u064a\u0627\u062a\u0647.",
  actionFailed:
    "\u062a\u0639\u0630\u0631 \u062a\u0646\u0641\u064a\u0630 \u0627\u0644\u0625\u062c\u0631\u0627\u0621.",
  deleteTitle:
    "\u062d\u0630\u0641 \u0627\u0644\u0639\u0645\u064a\u0644 \u0646\u0647\u0627\u0626\u064a\u064b\u0627",
  deleteWarning:
    "\u0647\u0630\u0627 \u0627\u0644\u0625\u062c\u0631\u0627\u0621 \u062f\u0627\u0626\u0645 \u0648\u0644\u0627 \u064a\u0645\u0643\u0646 \u0627\u0644\u062a\u0631\u0627\u062c\u0639 \u0639\u0646\u0647. \u0627\u0643\u062a\u0628 \u0645\u0639\u0631\u0641 \u0627\u0644\u0639\u0645\u064a\u0644 \u0628\u0627\u0644\u0643\u0627\u0645\u0644 \u0644\u0644\u062a\u0623\u0643\u064a\u062f.",
  confirmation:
    "\u0645\u0639\u0631\u0641 \u0627\u0644\u0639\u0645\u064a\u0644",
  cancel:
    "\u0625\u0644\u063a\u0627\u0621",
  confirmDelete:
    "\u062a\u0623\u0643\u064a\u062f \u0627\u0644\u062d\u0630\u0641",
  activeCount:
    "\u0646\u0634\u0637",
} as const;

const numberFormatter =
  new Intl.NumberFormat("ar");

const dateFormatter =
  new Intl.DateTimeFormat(
    "ar",
    {
      dateStyle: "medium",
    },
  );

function formatDate(
  value: string,
): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return dateFormatter.format(date);
}

async function readErrorMessage(
  response: Response,
): Promise<string> {
  const payload = (
    await response
      .json()
      .catch(() => null)
  ) as ErrorPayload | null;

  if (response.status === 403) {
    return copy.permissionDenied;
  }

  if (response.status === 409) {
    return copy.conflict;
  }

  if (
    typeof payload?.detail === "string" &&
    payload.detail.trim()
  ) {
    return payload.detail;
  }

  return copy.actionFailed;
}

function recomputeStatusSummary(
  items: TenantDirectoryItem[],
  current: TenantDirectoryResponse,
): TenantDirectoryResponse {
  return {
    ...current,
    items,
    summary: {
      ...current.summary,
      total: items.length,
      active: items.filter(
        (item) => item.is_active,
      ).length,
      inactive: items.filter(
        (item) => !item.is_active,
      ).length,
    },
  };
}

export function TenantsView() {
  const [data, setData] =
    useState<TenantDirectoryResponse | null>(
      null,
    );
  const [isLoading, setIsLoading] =
    useState(true);
  const [loadError, setLoadError] =
    useState<string | null>(null);
  const [actionError, setActionError] =
    useState<string | null>(null);
  const [search, setSearch] =
    useState("");
  const [statusFilter, setStatusFilter] =
    useState<StatusFilter>("all");
  const [busyTenantId, setBusyTenantId] =
    useState<string | null>(null);
  const [deleteTenant, setDeleteTenant] =
    useState<TenantDirectoryItem | null>(
      null,
    );
  const [deleteConfirmation, setDeleteConfirmation] =
    useState("");

  const requestDirectory = useCallback(
    async (
      signal?: AbortSignal,
    ): Promise<TenantDirectoryResponse> => {
      const response = await fetch(
        "/api/tenants",
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
          "/?next=%2Fdashboard%2Ftenants",
        );

        throw new Error(
          "Admin session is not active.",
        );
      }

      if (!response.ok) {
        throw new Error(
          `Tenant directory failed: ${response.status}`,
        );
      }

      return (
        await response.json()
      ) as TenantDirectoryResponse;
    },
    [],
  );

  const refreshDirectory = useCallback(
    async () => {
      setIsLoading(true);
      setLoadError(null);

      try {
        const payload =
          await requestDirectory();

        setData(payload);
      } catch {
        setLoadError(copy.loadError);
      } finally {
        setIsLoading(false);
      }
    },
    [requestDirectory],
  );

  useEffect(() => {
    const controller =
      new AbortController();

    async function loadInitial(): Promise<void> {
      try {
        const payload =
          await requestDirectory(
            controller.signal,
          );

        if (!controller.signal.aborted) {
          setData(payload);
        }
      } catch {
        if (!controller.signal.aborted) {
          setLoadError(copy.loadError);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadInitial();

    return () => {
      controller.abort();
    };
  }, [requestDirectory]);

  const visibleItems = useMemo(() => {
    if (data === null) {
      return [];
    }

    const normalizedSearch =
      search.trim().toLocaleLowerCase();

    return data.items.filter((tenant) => {
      const matchesSearch =
        normalizedSearch.length === 0 ||
        tenant.name
          .toLocaleLowerCase()
          .includes(normalizedSearch) ||
        tenant.id
          .toLocaleLowerCase()
          .includes(normalizedSearch);

      const matchesStatus =
        statusFilter === "all" ||
        (
          statusFilter === "active" &&
          tenant.is_active
        ) ||
        (
          statusFilter === "inactive" &&
          !tenant.is_active
        );

      return (
        matchesSearch &&
        matchesStatus
      );
    });
  }, [
    data,
    search,
    statusFilter,
  ]);

  async function changeTenantStatus(
    tenant: TenantDirectoryItem,
  ): Promise<void> {
    setBusyTenantId(tenant.id);
    setActionError(null);

    try {
      const response = await fetch(
        `/api/tenants/${
          encodeURIComponent(tenant.id)
        }/status`,
        {
          method: "PATCH",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type":
              "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            is_active: !tenant.is_active,
          }),
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard%2Ftenants",
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readErrorMessage(response),
        );
        return;
      }

      const updated = (
        await response.json()
      ) as {
        is_active: boolean;
        updated_at: string;
      };

      setData((current) => {
        if (current === null) {
          return current;
        }

        const items = current.items.map(
          (item) =>
            item.id === tenant.id
              ? {
                  ...item,
                  is_active:
                    updated.is_active,
                  updated_at:
                    updated.updated_at,
                }
              : item,
        );

        return recomputeStatusSummary(
          items,
          current,
        );
      });
    } catch {
      setActionError(copy.actionFailed);
    } finally {
      setBusyTenantId(null);
    }
  }

  async function confirmPermanentDelete(): Promise<void> {
    if (
      deleteTenant === null ||
      deleteConfirmation !== deleteTenant.id
    ) {
      return;
    }

    setBusyTenantId(deleteTenant.id);
    setActionError(null);

    try {
      const response = await fetch(
        `/api/tenants/${
          encodeURIComponent(deleteTenant.id)
        }?confirm=${
          encodeURIComponent(
            deleteConfirmation,
          )
        }`,
        {
          method: "DELETE",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            Accept: "application/json",
          },
        },
      );

      if (response.status === 401) {
        window.location.assign(
          "/?next=%2Fdashboard%2Ftenants",
        );
        return;
      }

      if (!response.ok) {
        setActionError(
          await readErrorMessage(response),
        );
        return;
      }

      setData((current) => {
        if (current === null) {
          return current;
        }

        const removed = current.items.find(
          (item) =>
            item.id === deleteTenant.id,
        );

        const items = current.items.filter(
          (item) =>
            item.id !== deleteTenant.id,
        );

        const next =
          recomputeStatusSummary(
            items,
            current,
          );

        if (!removed) {
          return next;
        }

        return {
          ...next,
          summary: {
            ...next.summary,
            agents_total:
              next.summary.agents_total -
              removed.agents_total,
            agents_active:
              next.summary.agents_active -
              removed.agents_active,
            api_keys_total:
              next.summary.api_keys_total -
              removed.api_keys_total,
            api_keys_active:
              next.summary.api_keys_active -
              removed.api_keys_active,
          },
        };
      });

      setDeleteTenant(null);
      setDeleteConfirmation("");
    } catch {
      setActionError(copy.actionFailed);
    } finally {
      setBusyTenantId(null);
    }
  }

  if (isLoading && data === null) {
    return (
      <main className="tenants-page">
        <section className="tenants-state">
          <LoaderCircle
            className="tenants-spinner"
            aria-hidden="true"
          />
          <h2>{copy.loading}</h2>

          <div className="tenants-skeleton">
            <span />
            <span />
            <span />
            <span />
          </div>
        </section>
      </main>
    );
  }

  if (loadError && data === null) {
    return (
      <main className="tenants-page">
        <section className="tenants-state">
          <AlertTriangle aria-hidden="true" />
          <h2>{loadError}</h2>

          <button
            type="button"
            onClick={() => {
              void refreshDirectory();
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
      label: copy.total,
      value: data.summary.total,
      icon: UsersRound,
    },
    {
      label: copy.active,
      value: data.summary.active,
      icon: CheckCircle2,
    },
    {
      label: copy.agents,
      value: data.summary.agents_total,
      icon: Bot,
    },
    {
      label: copy.keys,
      value: data.summary.api_keys_active,
      icon: KeyRound,
    },
  ];

  return (
    <main className="tenants-page">
      <section className="tenants-header">
        <div>
          <span className="tenants-header__eyebrow">
            <UsersRound aria-hidden="true" />
            {copy.eyebrow}
          </span>

          <h2>{copy.title}</h2>
          <p>{copy.description}</p>
        </div>

        <button
          className="tenants-refresh"
          type="button"
          disabled={isLoading}
          onClick={() => {
            void refreshDirectory();
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

      <section className="tenants-metrics">
        {metrics.map((metric) => {
          const Icon = metric.icon;

          return (
            <article
              key={metric.label}
              className="tenants-metric"
            >
              <span>
                <Icon aria-hidden="true" />
              </span>

              <div>
                <small>{metric.label}</small>
                <strong>
                  {numberFormatter.format(
                    metric.value,
                  )}
                </strong>
              </div>
            </article>
          );
        })}
      </section>

      {data.status === "partial" && (
        <div className="tenants-warning">
          <AlertTriangle aria-hidden="true" />
          <span>{copy.partial}</span>
        </div>
      )}

      {actionError && (
        <div
          className="tenants-action-error"
          role="alert"
        >
          <AlertTriangle aria-hidden="true" />
          <span>{actionError}</span>

          <button
            type="button"
            aria-label="\u0625\u063a\u0644\u0627\u0642"
            onClick={() => {
              setActionError(null);
            }}
          >
            <X aria-hidden="true" />
          </button>
        </div>
      )}

      <section className="tenants-directory">
        <header className="tenants-directory__toolbar">
          <div className="tenants-search">
            <Search aria-hidden="true" />

            <input
              type="search"
              value={search}
              placeholder={copy.search}
              aria-label={copy.search}
              onChange={(event) => {
                setSearch(event.target.value);
              }}
            />
          </div>

          <div
            className="tenants-filters"
            aria-label={copy.status}
          >
            {(
              [
                ["all", copy.all],
                ["active", copy.activeFilter],
                ["inactive", copy.inactiveFilter],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                className={
                  statusFilter === value
                    ? "is-active"
                    : undefined
                }
                onClick={() => {
                  setStatusFilter(value);
                }}
              >
                {label}
              </button>
            ))}
          </div>
        </header>

        <div
          className="tenants-table"
          role="table"
          aria-label={copy.title}
        >
          <div
            className="tenants-table__head"
            role="row"
          >
            <span role="columnheader">
              {copy.client}
            </span>
            <span role="columnheader">
              {copy.status}
            </span>
            <span role="columnheader">
              {copy.agentsColumn}
            </span>
            <span role="columnheader">
              {copy.keysColumn}
            </span>
            <span role="columnheader">
              {copy.created}
            </span>
            <span role="columnheader">
              {copy.actions}
            </span>
          </div>

          {visibleItems.length === 0 ? (
            <div className="tenants-empty">
              <UsersRound aria-hidden="true" />
              <p>{copy.empty}</p>
            </div>
          ) : (
            visibleItems.map((tenant) => {
              const isBusy =
                busyTenantId === tenant.id;

              return (
                <article
                  key={tenant.id}
                  className="tenants-row"
                  role="row"
                >
                  <div
                    className="tenants-row__identity"
                    role="cell"
                  >
                    <span>
                      {tenant.name
                        .trim()
                        .charAt(0)
                        .toUpperCase() || "A"}
                    </span>

                    <div>
                      <strong>
                        {tenant.name}
                      </strong>
                      <code dir="ltr">
                        {tenant.id}
                      </code>
                    </div>
                  </div>

                  <div role="cell">
                    <span
                      className={
                        tenant.is_active
                          ? "tenant-status is-active"
                          : "tenant-status"
                      }
                    >
                      <i />
                      {tenant.is_active
                        ? copy.activeState
                        : copy.inactiveState}
                    </span>
                  </div>

                  <div
                    className="tenant-count"
                    role="cell"
                  >
                    <strong>
                      {numberFormatter.format(
                        tenant.agents_total,
                      )}
                    </strong>
                    <small>
                      {numberFormatter.format(
                        tenant.agents_active,
                      )}{" "}
                      {copy.activeCount}
                    </small>
                  </div>

                  <div
                    className="tenant-count"
                    role="cell"
                  >
                    <strong>
                      {numberFormatter.format(
                        tenant.api_keys_total,
                      )}
                    </strong>
                    <small>
                      {numberFormatter.format(
                        tenant.api_keys_active,
                      )}{" "}
                      {copy.activeCount}
                    </small>
                  </div>

                  <div
                    className="tenant-created"
                    role="cell"
                  >
                    <CalendarDays aria-hidden="true" />
                    {formatDate(
                      tenant.created_at,
                    )}
                  </div>

                  <div
                    className="tenant-actions"
                    role="cell"
                  >
                    <button
                      type="button"
                      className="tenant-action"
                      disabled={isBusy}
                      title={
                        tenant.is_active
                          ? copy.suspend
                          : copy.activate
                      }
                      onClick={() => {
                        void changeTenantStatus(
                          tenant,
                        );
                      }}
                    >
                      {isBusy ? (
                        <LoaderCircle
                          className="tenants-spinner"
                          aria-hidden="true"
                        />
                      ) : tenant.is_active ? (
                        <PowerOff aria-hidden="true" />
                      ) : (
                        <Power aria-hidden="true" />
                      )}

                      <span>
                        {tenant.is_active
                          ? copy.suspend
                          : copy.activate}
                      </span>
                    </button>

                    <button
                      type="button"
                      className="tenant-action is-danger"
                      disabled={isBusy}
                      title={copy.delete}
                      onClick={() => {
                        setDeleteTenant(tenant);
                        setDeleteConfirmation("");
                        setActionError(null);
                      }}
                    >
                      <Trash2 aria-hidden="true" />
                      <span>{copy.delete}</span>
                    </button>
                  </div>
                </article>
              );
            })
          )}
        </div>
      </section>

      {deleteTenant && (
        <div className="tenant-dialog-backdrop">
          <section
            className="tenant-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="tenant-delete-title"
          >
            <header>
              <span>
                <AlertTriangle aria-hidden="true" />
              </span>

              <button
                type="button"
                aria-label="\u0625\u063a\u0644\u0627\u0642"
                disabled={
                  busyTenantId ===
                  deleteTenant.id
                }
                onClick={() => {
                  setDeleteTenant(null);
                  setDeleteConfirmation("");
                }}
              >
                <X aria-hidden="true" />
              </button>
            </header>

            <h3 id="tenant-delete-title">
              {copy.deleteTitle}
            </h3>

            <p>{copy.deleteWarning}</p>

            <strong className="tenant-dialog__name">
              {deleteTenant.name}
            </strong>

            <code
              className="tenant-dialog__id"
              dir="ltr"
            >
              {deleteTenant.id}
            </code>

            <label htmlFor="tenant-delete-confirmation">
              {copy.confirmation}
            </label>

            <input
              id="tenant-delete-confirmation"
              type="text"
              dir="ltr"
              autoComplete="off"
              value={deleteConfirmation}
              onChange={(event) => {
                setDeleteConfirmation(
                  event.target.value,
                );
              }}
            />

            <footer>
              <button
                type="button"
                disabled={
                  busyTenantId ===
                  deleteTenant.id
                }
                onClick={() => {
                  setDeleteTenant(null);
                  setDeleteConfirmation("");
                }}
              >
                {copy.cancel}
              </button>

              <button
                type="button"
                className="is-danger"
                disabled={
                  deleteConfirmation !==
                    deleteTenant.id ||
                  busyTenantId ===
                    deleteTenant.id
                }
                onClick={() => {
                  void confirmPermanentDelete();
                }}
              >
                {busyTenantId ===
                deleteTenant.id ? (
                  <LoaderCircle
                    className="tenants-spinner"
                    aria-hidden="true"
                  />
                ) : (
                  <Trash2 aria-hidden="true" />
                )}

                {copy.confirmDelete}
              </button>
            </footer>
          </section>
        </div>
      )}
    </main>
  );
}
