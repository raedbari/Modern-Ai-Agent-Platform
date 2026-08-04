"use client";

import {
  Activity,
  AlertTriangle,
  Bot,
  BookOpenCheck,
  CheckCircle2,
  Database,
  FileText,
  Layers3,
  LoaderCircle,
  RefreshCw,
  Search,
} from "lucide-react";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  KnowledgeBaseRecord,
  KnowledgeDocumentRecord,
  KnowledgeIngestionJobRecord,
} from "@/lib/knowledge/contracts";

import type {
  TenantDirectoryItem,
  TenantDirectoryResponse,
} from "@/lib/tenants/contracts";

import styles from "./knowledge-bases-view.module.css";

type DetailTab =
  | "documents"
  | "jobs";

const copy = {
  eyebrow:
    "إدارة المعرفة",
  title:
    "مصادر المعرفة",
  description:
    "راقب قواعد المعرفة والمستندات وعمليات الفهرسة لكل عميل من مساحة إدارية واحدة.",
  readOnly:
    "هذه المرحلة تعرض البيانات الحية فقط. الإنشاء والرفع وإعادة الفهرسة ستضاف بعد اعتماد واجهة القراءة.",
  refresh:
    "تحديث البيانات",
  tenant:
    "العميل",
  chooseTenant:
    "اختر العميل",
  search:
    "ابحث باسم قاعدة المعرفة أو المعرّف",
  totalBases:
    "قواعد المعرفة",
  totalDocuments:
    "إجمالي المستندات",
  readyDocuments:
    "المستندات الجاهزة",
  totalChunks:
    "المقاطع المفهرسة",
  bases:
    "قواعد العميل",
  baseCount:
    "قاعدة معرفة",
  active:
    "نشطة",
  inactive:
    "متوقفة",
  documents:
    "المستندات",
  jobs:
    "عمليات الفهرسة",
  chunks:
    "مقطع",
  assignedAgents:
    "الوكلاء المرتبطون",
  noAssignedAgents:
    "لا يوجد وكلاء مرتبطون",
  updated:
    "آخر تحديث",
  created:
    "تاريخ الإنشاء",
  noDescription:
    "لا يوجد وصف لهذه القاعدة.",
  pending:
    "قيد الانتظار",
  processing:
    "قيد المعالجة",
  ready:
    "جاهز",
  failed:
    "فشل",
  succeeded:
    "نجحت",
  attempts:
    "المحاولات",
  availableAt:
    "متاحة منذ",
  completedAt:
    "اكتملت في",
  notCompleted:
    "لم تكتمل بعد",
  source:
    "المصدر",
  mimeType:
    "نوع الملف",
  fileSize:
    "حجم الملف",
  latestJob:
    "آخر عملية",
  noLatestJob:
    "لا توجد عملية فهرسة",
  failureReason:
    "سبب الفشل",
  lastError:
    "آخر خطأ",
  noDocuments:
    "لا توجد مستندات داخل قاعدة المعرفة المحددة.",
  noJobs:
    "لا توجد عمليات فهرسة داخل قاعدة المعرفة المحددة.",
  noBases:
    "لا توجد قواعد معرفة لهذا العميل.",
  noSearchResults:
    "لا توجد قواعد معرفة تطابق البحث.",
  noTenants:
    "لا يوجد عملاء متاحون.",
  loadingTenants:
    "جاري تحميل العملاء",
  loadingBases:
    "جاري تحميل قواعد المعرفة",
  loadingDetails:
    "جاري تحميل تفاصيل قاعدة المعرفة",
  tenantsError:
    "تعذر تحميل قائمة العملاء.",
  basesError:
    "تعذر تحميل قواعد المعرفة لهذا العميل.",
  detailsError:
    "تعذر تحميل تفاصيل قاعدة المعرفة.",
  retry:
    "إعادة المحاولة",
  unknown:
    "غير متوفر",
} as const;

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

function formatDate(
  value: string | null,
): string {
  if (!value) {
    return copy.unknown;
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return copy.unknown;
  }

  return dateFormatter.format(date);
}

function formatBytes(
  value: number,
): string {
  if (
    !Number.isFinite(value) ||
    value < 0
  ) {
    return copy.unknown;
  }

  const units = [
    "بايت",
    "ك.ب",
    "م.ب",
    "ج.ب",
  ];

  let amount = value;
  let unitIndex = 0;

  while (
    amount >= 1024 &&
    unitIndex < units.length - 1
  ) {
    amount /= 1024;
    unitIndex += 1;
  }

  const normalized =
    unitIndex === 0
      ? Math.round(amount)
      : Math.round(amount * 10) / 10;

  return `${
    numberFormatter.format(normalized)
  } ${units[unitIndex]}`;
}

function statusLabel(
  status: string,
): string {
  if (status === "active") {
    return copy.active;
  }

  if (status === "inactive") {
    return copy.inactive;
  }

  if (status === "pending") {
    return copy.pending;
  }

  if (status === "processing") {
    return copy.processing;
  }

  if (status === "ready") {
    return copy.ready;
  }

  if (status === "failed") {
    return copy.failed;
  }

  if (status === "succeeded") {
    return copy.succeeded;
  }

  return status.replaceAll("_", " ");
}

function statusClass(
  status: string,
): string {
  if (
    status === "active" ||
    status === "ready" ||
    status === "succeeded"
  ) {
    return styles.statusSuccess;
  }

  if (status === "processing") {
    return styles.statusProcessing;
  }

  if (status === "pending") {
    return styles.statusPending;
  }

  if (
    status === "failed" ||
    status === "inactive"
  ) {
    return styles.statusFailed;
  }

  return styles.statusNeutral;
}

function isAbortError(
  error: unknown,
): boolean {
  return (
    error instanceof DOMException &&
    error.name === "AbortError"
  );
}

async function requestJson<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(
    path,
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
      "/?next=%2Fdashboard%2Fknowledge-bases",
    );

    throw new Error(
      "Admin session is not active.",
    );
  }

  if (!response.ok) {
    throw new Error(
      `Request failed: ${response.status}`,
    );
  }

  return await response.json() as T;
}

export function KnowledgeBasesView() {
  const [tenants, setTenants] =
    useState<TenantDirectoryItem[]>([]);

  const [
    selectedTenantId,
    setSelectedTenantId,
  ] = useState("");

  const [bases, setBases] =
    useState<KnowledgeBaseRecord[]>([]);

  const [
    selectedBaseId,
    setSelectedBaseId,
  ] = useState("");

  const [detail, setDetail] =
    useState<KnowledgeBaseRecord | null>(
      null,
    );

  const [documents, setDocuments] =
    useState<KnowledgeDocumentRecord[]>([]);

  const [jobs, setJobs] =
    useState<
      KnowledgeIngestionJobRecord[]
    >([]);

  const [search, setSearch] =
    useState("");

  const [activeTab, setActiveTab] =
    useState<DetailTab>("documents");

  const [
    isLoadingTenants,
    setIsLoadingTenants,
  ] = useState(true);

  const [
    isLoadingBases,
    setIsLoadingBases,
  ] = useState(false);

  const [
    isLoadingDetails,
    setIsLoadingDetails,
  ] = useState(false);

  const [tenantsError, setTenantsError] =
    useState<string | null>(null);

  const [basesError, setBasesError] =
    useState<string | null>(null);

  const [detailsError, setDetailsError] =
    useState<string | null>(null);

  const [
    refreshVersion,
    setRefreshVersion,
  ] = useState(0);

  const loadTenants = useCallback(
    async (
      signal?: AbortSignal,
    ): Promise<void> => {
      try {
        const payload =
          await requestJson<
            TenantDirectoryResponse
          >(
            "/api/tenants",
            signal,
          );

        setTenants(payload.items);
        setTenantsError(null);
        setIsLoadingBases(
          payload.items.length > 0,
        );

        setSelectedTenantId(
          (current) => {
            if (
              current &&
              payload.items.some(
                (tenant) =>
                  tenant.id === current,
              )
            ) {
              return current;
            }

            return (
              payload.items.find(
                (tenant) =>
                  tenant.is_active,
              )?.id ??
              payload.items[0]?.id ??
              ""
            );
          },
        );
      } catch (error) {
        if (!isAbortError(error)) {
          setTenantsError(
            copy.tenantsError,
          );
        }
      } finally {
        if (!signal?.aborted) {
          setIsLoadingTenants(false);
        }
      }
    },
    [],
  );

  useEffect(() => {
    const controller =
      new AbortController();

    async function loadInitialTenants(): Promise<void> {
      try {
        const payload =
          await requestJson<
            TenantDirectoryResponse
          >(
            "/api/tenants",
            controller.signal,
          );

        if (controller.signal.aborted) {
          return;
        }

        setTenants(payload.items);
        setTenantsError(null);
        setIsLoadingBases(
          payload.items.length > 0,
        );

        setSelectedTenantId(
          (current) => {
            if (
              current &&
              payload.items.some(
                (tenant) =>
                  tenant.id === current,
              )
            ) {
              return current;
            }

            return (
              payload.items.find(
                (tenant) =>
                  tenant.is_active,
              )?.id ??
              payload.items[0]?.id ??
              ""
            );
          },
        );
      } catch (error) {
        if (
          !controller.signal.aborted &&
          !isAbortError(error)
        ) {
          setTenantsError(
            copy.tenantsError,
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoadingTenants(false);
        }
      }
    }

    void loadInitialTenants();

    return () => {
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (!selectedTenantId) {
      return;
    }

    const controller =
      new AbortController();

    void requestJson<
      KnowledgeBaseRecord[]
    >(
      `/api/knowledge-bases/${
        encodeURIComponent(
          selectedTenantId,
        )
      }`,
      controller.signal,
    )
      .then((items) => {
        if (controller.signal.aborted) {
          return;
        }

        const sorted = [...items].sort(
          (left, right) =>
            Date.parse(right.updated_at) -
            Date.parse(left.updated_at),
        );

        setBasesError(null);
        setBases(sorted);
        setDetail(null);
        setDocuments([]);
        setJobs([]);
        setIsLoadingDetails(
          sorted.length > 0,
        );

        setSelectedBaseId(
          sorted[0]?.id ?? "",
        );
      })
      .catch((error: unknown) => {
        if (!isAbortError(error)) {
          setBasesError(
            copy.basesError,
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoadingBases(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [
    refreshVersion,
    selectedTenantId,
  ]);

  useEffect(() => {
    if (
      !selectedTenantId ||
      !selectedBaseId
    ) {
      return;
    }

    const controller =
      new AbortController();

    const tenantId =
      encodeURIComponent(
        selectedTenantId,
      );

    const knowledgeBaseId =
      encodeURIComponent(
        selectedBaseId,
      );

    void Promise.all([
      requestJson<KnowledgeBaseRecord>(
        `/api/knowledge-bases/${
          tenantId
        }/${knowledgeBaseId}`,
        controller.signal,
      ),
      requestJson<
        KnowledgeDocumentRecord[]
      >(
        `/api/knowledge-bases/${
          tenantId
        }/${knowledgeBaseId}/documents`,
        controller.signal,
      ),
      requestJson<
        KnowledgeIngestionJobRecord[]
      >(
        `/api/knowledge-bases/${
          tenantId
        }/${knowledgeBaseId}/ingestion-jobs?limit=100`,
        controller.signal,
      ),
    ])
      .then(
        ([
          detailPayload,
          documentPayload,
          jobPayload,
        ]) => {
          if (controller.signal.aborted) {
            return;
          }

          setDetailsError(null);
          setDetail(detailPayload);
          setDocuments(documentPayload);
          setJobs(jobPayload);
        },
      )
      .catch((error: unknown) => {
        if (!isAbortError(error)) {
          setDetailsError(
            copy.detailsError,
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoadingDetails(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [
    refreshVersion,
    selectedBaseId,
    selectedTenantId,
  ]);

  const selectedTenant = useMemo(
    () =>
      tenants.find(
        (tenant) =>
          tenant.id === selectedTenantId,
      ) ?? null,
    [
      selectedTenantId,
      tenants,
    ],
  );

  const visibleBases = useMemo(() => {
    const normalizedSearch =
      search
        .trim()
        .toLocaleLowerCase();

    if (!normalizedSearch) {
      return bases;
    }

    return bases.filter(
      (item) =>
        item.name
          .toLocaleLowerCase()
          .includes(normalizedSearch) ||
        item.id
          .toLocaleLowerCase()
          .includes(normalizedSearch) ||
        item.description
          .toLocaleLowerCase()
          .includes(normalizedSearch),
    );
  }, [
    bases,
    search,
  ]);

  const currentBase =
    detail ??
    bases.find(
      (item) =>
        item.id === selectedBaseId,
    ) ??
    null;

  const totals = useMemo(
    () => ({
      bases: bases.length,
      documents: bases.reduce(
        (total, item) =>
          total + item.document_count,
        0,
      ),
      readyDocuments: bases.reduce(
        (total, item) =>
          total +
          item.ready_document_count,
        0,
      ),
      chunks: bases.reduce(
        (total, item) =>
          total + item.chunk_count,
        0,
      ),
    }),
    [bases],
  );

  const isRefreshing =
    isLoadingBases ||
    isLoadingDetails;

  if (
    isLoadingTenants &&
    tenants.length === 0
  ) {
    return (
      <main className={styles.page}>
        <section className={styles.fullState}>
          <LoaderCircle
            className={styles.spinner}
            aria-hidden="true"
          />
          <h2>{copy.loadingTenants}</h2>
        </section>
      </main>
    );
  }

  if (
    tenantsError &&
    tenants.length === 0
  ) {
    return (
      <main className={styles.page}>
        <section className={styles.fullState}>
          <AlertTriangle aria-hidden="true" />
          <h2>{tenantsError}</h2>

          <button
            type="button"
            onClick={() => {
              setIsLoadingTenants(true);
              setTenantsError(null);
              void loadTenants();
            }}
          >
            <RefreshCw aria-hidden="true" />
            {copy.retry}
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div
          className={styles.heroGlow}
          aria-hidden="true"
        />

        <div className={styles.heroContent}>
          <span className={styles.eyebrow}>
            <BookOpenCheck aria-hidden="true" />
            {copy.eyebrow}
          </span>

          <h2>{copy.title}</h2>
          <p>{copy.description}</p>
        </div>

        <button
          className={styles.refreshButton}
          type="button"
          disabled={isRefreshing}
          onClick={() => {
            setRefreshVersion(
              (current) => current + 1,
            );
          }}
        >
          <RefreshCw
            className={
              isRefreshing
                ? styles.spinner
                : undefined
            }
            aria-hidden="true"
          />
          {copy.refresh}
        </button>
      </section>

      <div className={styles.readOnlyNote}>
        <CheckCircle2 aria-hidden="true" />
        <span>{copy.readOnly}</span>
      </div>

      <section className={styles.controls}>
        <label className={styles.selectField}>
          <span>
            <Database aria-hidden="true" />
            {copy.tenant}
          </span>

          <select
            value={selectedTenantId}
            disabled={tenants.length === 0}
            onChange={(event) => {
              const tenantId =
                event.target.value;

              setSearch("");
              setActiveTab("documents");
              setBases([]);
              setSelectedBaseId("");
              setDetail(null);
              setDocuments([]);
              setJobs([]);
              setBasesError(null);
              setDetailsError(null);
              setIsLoadingBases(
                tenantId.length > 0,
              );
              setIsLoadingDetails(false);
              setSelectedTenantId(
                tenantId,
              );
            }}
          >
            {tenants.length === 0 && (
              <option value="">
                {copy.chooseTenant}
              </option>
            )}

            {tenants.map((tenant) => (
              <option
                key={tenant.id}
                value={tenant.id}
              >
                {tenant.name}
                {" ? "}
                {tenant.is_active
                  ? copy.active
                  : copy.inactive}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.searchField}>
          <Search aria-hidden="true" />

          <input
            type="search"
            value={search}
            placeholder={copy.search}
            aria-label={copy.search}
            onChange={(event) => {
              setSearch(
                event.target.value,
              );
            }}
          />
        </label>

        {selectedTenant && (
          <div className={styles.tenantSummary}>
            <span>
              {selectedTenant.name
                .trim()
                .charAt(0)
                .toUpperCase() || "A"}
            </span>

            <div>
              <strong>
                {selectedTenant.name}
              </strong>
              <code dir="ltr">
                {selectedTenant.id}
              </code>
            </div>
          </div>
        )}
      </section>

      <section className={styles.metrics}>
        {[
          {
            label: copy.totalBases,
            value: totals.bases,
            icon: Database,
          },
          {
            label: copy.totalDocuments,
            value: totals.documents,
            icon: FileText,
          },
          {
            label: copy.readyDocuments,
            value: totals.readyDocuments,
            icon: CheckCircle2,
          },
          {
            label: copy.totalChunks,
            value: totals.chunks,
            icon: Layers3,
          },
        ].map((metric) => {
          const Icon = metric.icon;

          return (
            <article
              key={metric.label}
              className={styles.metricCard}
            >
              <span
                className={styles.metricIcon}
              >
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

      <section className={styles.workspace}>
        <aside className={styles.basePanel}>
          <header className={styles.panelHeader}>
            <div>
              <span>
                <Database aria-hidden="true" />
              </span>

              <div>
                <h3>{copy.bases}</h3>
                <p>
                  {numberFormatter.format(
                    visibleBases.length,
                  )}{" "}
                  {copy.baseCount}
                </p>
              </div>
            </div>
          </header>

          <div className={styles.baseList}>
            {isLoadingBases &&
            bases.length === 0 ? (
              <div className={styles.panelState}>
                <LoaderCircle
                  className={styles.spinner}
                  aria-hidden="true"
                />
                <p>{copy.loadingBases}</p>
              </div>
            ) : basesError ? (
              <div className={styles.panelState}>
                <AlertTriangle
                  aria-hidden="true"
                />
                <p>{basesError}</p>

                <button
                  type="button"
                  onClick={() => {
                    setRefreshVersion(
                      (current) =>
                        current + 1,
                    );
                  }}
                >
                  {copy.retry}
                </button>
              </div>
            ) : tenants.length === 0 ? (
              <div className={styles.panelState}>
                <Database aria-hidden="true" />
                <p>{copy.noTenants}</p>
              </div>
            ) : bases.length === 0 ? (
              <div className={styles.panelState}>
                <BookOpenCheck
                  aria-hidden="true"
                />
                <p>{copy.noBases}</p>
              </div>
            ) : visibleBases.length === 0 ? (
              <div className={styles.panelState}>
                <Search aria-hidden="true" />
                <p>{copy.noSearchResults}</p>
              </div>
            ) : (
              visibleBases.map((item) => {
                const selected =
                  item.id === selectedBaseId;

                return (
                  <button
                    key={item.id}
                    className={
                      selected
                        ? `${styles.baseItem} ${styles.baseItemSelected}`
                        : styles.baseItem
                    }
                    type="button"
                    onClick={() => {
                      setActiveTab(
                        "documents",
                      );
                      setDetail(null);
                      setDocuments([]);
                      setJobs([]);
                      setDetailsError(null);
                      setIsLoadingDetails(true);
                      setSelectedBaseId(
                        item.id,
                      );
                    }}
                  >
                    <div
                      className={
                        styles.baseItemTop
                      }
                    >
                      <span
                        className={
                          styles.baseIcon
                        }
                      >
                        <Database
                          aria-hidden="true"
                        />
                      </span>

                      <span
                        className={`${
                          styles.statusBadge
                        } ${
                          statusClass(
                            item.status,
                          )
                        }`}
                      >
                        {statusLabel(
                          item.status,
                        )}
                      </span>
                    </div>

                    <strong>{item.name}</strong>

                    <code dir="ltr">
                      {item.id}
                    </code>

                    <div
                      className={
                        styles.baseItemStats
                      }
                    >
                      <span>
                        <FileText
                          aria-hidden="true"
                        />
                        {numberFormatter.format(
                          item.document_count,
                        )}
                      </span>

                      <span>
                        <Layers3
                          aria-hidden="true"
                        />
                        {numberFormatter.format(
                          item.chunk_count,
                        )}
                      </span>

                      <span>
                        <Activity
                          aria-hidden="true"
                        />
                        {numberFormatter.format(
                          item.processing_job_count +
                          item.pending_job_count,
                        )}
                      </span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </aside>

        <article className={styles.detailPanel}>
          {isLoadingDetails &&
          currentBase === null ? (
            <div className={styles.detailState}>
              <LoaderCircle
                className={styles.spinner}
                aria-hidden="true"
              />
              <h3>{copy.loadingDetails}</h3>
            </div>
          ) : detailsError ? (
            <div className={styles.detailState}>
              <AlertTriangle
                aria-hidden="true"
              />
              <h3>{detailsError}</h3>

              <button
                type="button"
                onClick={() => {
                  setRefreshVersion(
                    (current) =>
                      current + 1,
                  );
                }}
              >
                <RefreshCw
                  aria-hidden="true"
                />
                {copy.retry}
              </button>
            </div>
          ) : currentBase === null ? (
            <div className={styles.detailState}>
              <BookOpenCheck
                aria-hidden="true"
              />
              <h3>{copy.noBases}</h3>
            </div>
          ) : (
            <>
              <header
                className={styles.detailHeader}
              >
                <div>
                  <span
                    className={
                      styles.detailEyebrow
                    }
                  >
                    <BookOpenCheck
                      aria-hidden="true"
                    />
                    {copy.eyebrow}
                  </span>

                  <div
                    className={
                      styles.detailTitleRow
                    }
                  >
                    <h3>
                      {currentBase.name}
                    </h3>

                    <span
                      className={`${
                        styles.statusBadge
                      } ${
                        statusClass(
                          currentBase.status,
                        )
                      }`}
                    >
                      {statusLabel(
                        currentBase.status,
                      )}
                    </span>
                  </div>

                  <code dir="ltr">
                    {currentBase.id}
                  </code>

                  <p>
                    {currentBase.description
                      .trim() ||
                      copy.noDescription}
                  </p>
                </div>

                {isLoadingDetails && (
                  <LoaderCircle
                    className={styles.spinner}
                    aria-label={
                      copy.loadingDetails
                    }
                  />
                )}
              </header>

              <section
                className={
                  styles.detailMetadata
                }
              >
                <div>
                  <small>{copy.created}</small>
                  <strong>
                    {formatDate(
                      currentBase.created_at,
                    )}
                  </strong>
                </div>

                <div>
                  <small>{copy.updated}</small>
                  <strong>
                    {formatDate(
                      currentBase.updated_at,
                    )}
                  </strong>
                </div>

                <div>
                  <small>
                    {copy.assignedAgents}
                  </small>

                  <strong>
                    {numberFormatter.format(
                      currentBase
                        .assigned_agent_ids
                        ?.length ?? 0,
                    )}
                  </strong>
                </div>

                <div>
                  <small>{copy.chunks}</small>
                  <strong>
                    {numberFormatter.format(
                      currentBase.chunk_count,
                    )}
                  </strong>
                </div>
              </section>

              <section
                className={styles.agentSection}
              >
                <div className={styles.sectionTitle}>
                  <Bot aria-hidden="true" />
                  <h4>{copy.assignedAgents}</h4>
                </div>

                {(
                  currentBase
                    .assigned_agent_ids ??
                  []
                ).length === 0 ? (
                  <p
                    className={
                      styles.emptyInline
                    }
                  >
                    {copy.noAssignedAgents}
                  </p>
                ) : (
                  <div
                    className={
                      styles.agentChips
                    }
                  >
                    {currentBase
                      .assigned_agent_ids
                      ?.map((agentId) => (
                        <code
                          key={agentId}
                          dir="ltr"
                        >
                          <Bot
                            aria-hidden="true"
                          />
                          {agentId}
                        </code>
                      ))}
                  </div>
                )}
              </section>

              <div className={styles.tabs}>
                <button
                  type="button"
                  className={
                    activeTab === "documents"
                      ? styles.tabActive
                      : undefined
                  }
                  onClick={() => {
                    setActiveTab(
                      "documents",
                    );
                  }}
                >
                  <FileText
                    aria-hidden="true"
                  />
                  {copy.documents}
                  <span>
                    {numberFormatter.format(
                      documents.length,
                    )}
                  </span>
                </button>

                <button
                  type="button"
                  className={
                    activeTab === "jobs"
                      ? styles.tabActive
                      : undefined
                  }
                  onClick={() => {
                    setActiveTab("jobs");
                  }}
                >
                  <Activity
                    aria-hidden="true"
                  />
                  {copy.jobs}
                  <span>
                    {numberFormatter.format(
                      jobs.length,
                    )}
                  </span>
                </button>
              </div>

              {activeTab === "documents" ? (
                <div
                  className={
                    styles.recordsList
                  }
                >
                  {documents.length === 0 ? (
                    <div
                      className={
                        styles.recordsEmpty
                      }
                    >
                      <FileText
                        aria-hidden="true"
                      />
                      <p>{copy.noDocuments}</p>
                    </div>
                  ) : (
                    documents.map(
                      (document) => (
                        <article
                          key={document.id}
                          className={
                            styles.recordCard
                          }
                        >
                          <div
                            className={
                              styles.recordHeader
                            }
                          >
                            <span
                              className={
                                styles.recordIcon
                              }
                            >
                              <FileText
                                aria-hidden="true"
                              />
                            </span>

                            <div
                              className={
                                styles.recordIdentity
                              }
                            >
                              <strong>
                                {
                                  document.original_filename
                                }
                              </strong>

                              <code dir="ltr">
                                {document.id}
                              </code>
                            </div>

                            <span
                              className={`${
                                styles.statusBadge
                              } ${
                                statusClass(
                                  document.status,
                                )
                              }`}
                            >
                              {statusLabel(
                                document.status,
                              )}
                            </span>
                          </div>

                          <dl
                            className={
                              styles.recordGrid
                            }
                          >
                            <div>
                              <dt>{copy.source}</dt>
                              <dd>
                                {
                                  document.source_name
                                }
                              </dd>
                            </div>

                            <div>
                              <dt>
                                {copy.mimeType}
                              </dt>
                              <dd dir="ltr">
                                {
                                  document.mime_type
                                }
                              </dd>
                            </div>

                            <div>
                              <dt>
                                {copy.fileSize}
                              </dt>
                              <dd>
                                {formatBytes(
                                  document.file_size_bytes,
                                )}
                              </dd>
                            </div>

                            <div>
                              <dt>{copy.chunks}</dt>
                              <dd>
                                {numberFormatter.format(
                                  document.chunk_count,
                                )}
                              </dd>
                            </div>

                            <div>
                              <dt>{copy.updated}</dt>
                              <dd>
                                {formatDate(
                                  document.updated_at,
                                )}
                              </dd>
                            </div>

                            <div>
                              <dt>
                                {copy.latestJob}
                              </dt>
                              <dd>
                                {document.latest_job
                                  ? statusLabel(
                                      document
                                        .latest_job
                                        .status,
                                    )
                                  : copy.noLatestJob}
                              </dd>
                            </div>
                          </dl>

                          {document.failure_reason && (
                            <div
                              className={
                                styles.errorMessage
                              }
                            >
                              <AlertTriangle
                                aria-hidden="true"
                              />

                              <div>
                                <strong>
                                  {
                                    copy.failureReason
                                  }
                                </strong>
                                <p>
                                  {
                                    document.failure_reason
                                  }
                                </p>
                              </div>
                            </div>
                          )}
                        </article>
                      ),
                    )
                  )}
                </div>
              ) : (
                <div
                  className={
                    styles.recordsList
                  }
                >
                  {jobs.length === 0 ? (
                    <div
                      className={
                        styles.recordsEmpty
                      }
                    >
                      <Activity
                        aria-hidden="true"
                      />
                      <p>{copy.noJobs}</p>
                    </div>
                  ) : (
                    jobs.map((job) => (
                      <article
                        key={job.id}
                        className={
                          styles.recordCard
                        }
                      >
                        <div
                          className={
                            styles.recordHeader
                          }
                        >
                          <span
                            className={
                              styles.recordIcon
                            }
                          >
                            <Activity
                              aria-hidden="true"
                            />
                          </span>

                          <div
                            className={
                              styles.recordIdentity
                            }
                          >
                            <strong>
                              {copy.latestJob}
                            </strong>

                            <code dir="ltr">
                              {job.id}
                            </code>
                          </div>

                          <span
                            className={`${
                              styles.statusBadge
                            } ${
                              statusClass(
                                job.status,
                              )
                            }`}
                          >
                            {statusLabel(
                              job.status,
                            )}
                          </span>
                        </div>

                        <dl
                          className={
                            styles.recordGrid
                          }
                        >
                          <div>
                            <dt>
                              {copy.assignedAgents}
                            </dt>
                            <dd dir="ltr">
                              {job.agent_id}
                            </dd>
                          </div>

                          <div>
                            <dt>
                              {copy.attempts}
                            </dt>
                            <dd>
                              {numberFormatter.format(
                                job.attempts,
                              )}
                              {" / "}
                              {numberFormatter.format(
                                job.max_attempts,
                              )}
                            </dd>
                          </div>

                          <div>
                            <dt>
                              {copy.availableAt}
                            </dt>
                            <dd>
                              {formatDate(
                                job.available_at,
                              )}
                            </dd>
                          </div>

                          <div>
                            <dt>
                              {copy.completedAt}
                            </dt>
                            <dd>
                              {job.completed_at
                                ? formatDate(
                                    job.completed_at,
                                  )
                                : copy.notCompleted}
                            </dd>
                          </div>

                          <div>
                            <dt>{copy.created}</dt>
                            <dd>
                              {formatDate(
                                job.created_at,
                              )}
                            </dd>
                          </div>

                          <div>
                            <dt>{copy.updated}</dt>
                            <dd>
                              {formatDate(
                                job.updated_at,
                              )}
                            </dd>
                          </div>
                        </dl>

                        {job.last_error && (
                          <div
                            className={
                              styles.errorMessage
                            }
                          >
                            <AlertTriangle
                              aria-hidden="true"
                            />

                            <div>
                              <strong>
                                {copy.lastError}
                              </strong>
                              <p>
                                {job.last_error}
                              </p>
                            </div>
                          </div>
                        )}
                      </article>
                    ))
                  )}
                </div>
              )}
            </>
          )}
        </article>
      </section>
    </main>
  );
}
