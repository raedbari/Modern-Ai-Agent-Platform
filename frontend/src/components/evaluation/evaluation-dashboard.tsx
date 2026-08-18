"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  FlaskConical,
  LoaderCircle,
  Play,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { components } from "@/lib/api/generated/admin-api";
import type {
  AgentDirectoryItem,
  AgentDirectoryResponse,
} from "@/lib/agents/contracts";

import styles from "./evaluation-dashboard.module.css";

type DatasetSummary = components["schemas"]["EvaluationDatasetSummaryResponse"];
type Dataset = components["schemas"]["EvaluationDataset"];
type EvaluationRun = components["schemas"]["EvaluationRunResponse"];
type CaseResult = components["schemas"]["EvaluationCaseResult"];

type DashboardData = {
  datasets: DatasetSummary[];
  runs: EvaluationRun[];
  agents: AgentDirectoryItem[];
};

const dateFormatter = new Intl.DateTimeFormat("ar", {
  dateStyle: "medium",
  timeStyle: "short",
});
const numberFormatter = new Intl.NumberFormat("ar", {
  maximumFractionDigits: 2,
});

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : dateFormatter.format(date);
}

function statusLabel(status: string): string {
  if (status === "running") return "قيد التشغيل";
  if (status === "completed") return "مكتمل";
  if (status === "failed") return "فشل";
  if (status === "passed") return "ناجحة";
  if (status === "error") return "خطأ";
  return "غير ناجحة";
}

function statusIcon(status: string) {
  if (status === "running") return <LoaderCircle className={styles.spinner} aria-hidden="true" />;
  if (status === "completed" || status === "passed") return <CheckCircle2 aria-hidden="true" />;
  return <XCircle aria-hidden="true" />;
}

async function responseError(response: Response): Promise<string> {
  const payload = await response.json().catch(() => null) as { detail?: unknown } | null;
  return typeof payload?.detail === "string"
    ? payload.detail
    : "تعذر إكمال الطلب. حاول مجددًا.";
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
  });
  if (response.status === 401) {
    window.location.assign(`/?next=${encodeURIComponent("/dashboard/evaluation")}`);
    throw new Error("انتهت الجلسة الإدارية.");
  }
  if (!response.ok) throw new Error(await responseError(response));
  return await response.json() as T;
}

function runStatusClass(status: string): string {
  return `${styles.status} ${
    status === "completed"
      ? styles.success
      : status === "running"
        ? styles.running
        : styles.failed
  }`;
}

function Metric({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className={styles.metric}>
      <span>{label}</span>
      <strong>{value === null ? "غير مقاس" : value}</strong>
    </div>
  );
}

function CaseResultCard({ result }: { result: CaseResult }) {
  const rag = result.rag_metrics;
  return (
    <details className={styles.caseCard}>
      <summary>
        <span className={runStatusClass(result.status)}>
          {statusIcon(result.status)}
          {statusLabel(result.status)}
        </span>
        <strong>{result.case_id}</strong>
        <span>{numberFormatter.format(result.latency_ms)} ms</span>
      </summary>
      <div className={styles.caseBody}>
        {result.response_content ? (
          <div className={styles.responseBlock}>
            <span>الاستجابة</span>
            <p>{result.response_content}</p>
          </div>
        ) : (
          <p className={styles.muted}>لم تُسجل استجابة نصية لهذه الحالة.</p>
        )}
        <div className={styles.caseMetrics}>
          <Metric label="Prompt tokens" value={result.prompt_tokens} />
          <Metric label="Completion tokens" value={result.completion_tokens} />
          <Metric label="Retrieval count" value={rag?.retrieval_count ?? null} />
          <Metric label="Citation count" value={rag?.citation_count ?? null} />
          <Metric label="Answer status" value={result.answer_status ?? null} />
          <Metric label="Model" value={result.model ?? null} />
        </div>
      </div>
    </details>
  );
}

export function EvaluationDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectedDatasetKey, setSelectedDatasetKey] = useState("");
  const [selectedAgentKey, setSelectedAgentKey] = useState("");
  const [datasetDetail, setDatasetDetail] = useState<Dataset | null>(null);
  const [datasetDetailLoading, setDatasetDetailLoading] = useState(false);
  const [selectedRun, setSelectedRun] = useState<EvaluationRun | null>(null);
  const [starting, setStarting] = useState(false);

  const loadDashboard = useCallback(async () => {
    setLoadError(null);
    try {
      const [datasets, runs, agentDirectory] = await Promise.all([
        fetchJson<DatasetSummary[]>("/api/evaluation/datasets"),
        fetchJson<EvaluationRun[]>("/api/evaluation/runs"),
        fetchJson<AgentDirectoryResponse>("/api/agents"),
      ]);
      const agents = agentDirectory.items.filter((item) => item.is_active);
      setData({ datasets, runs, agents });
      setSelectedDatasetKey((current) => current || (
        datasets[0] ? `${datasets[0].name}::${datasets[0].version}` : ""
      ));
      setSelectedAgentKey((current) => current || (
        agents[0] ? `${agents[0].tenant_id}::${agents[0].id}` : ""
      ));
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "تعذر تحميل بيانات التقييم.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadDashboard();
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [loadDashboard]);

  useEffect(() => {
    if (!selectedDatasetKey) {
      return;
    }
    const [name, version] = selectedDatasetKey.split("::");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      setDatasetDetailLoading(true);
      void fetchJson<Dataset>(
        `/api/evaluation/datasets/${encodeURIComponent(name)}/${encodeURIComponent(version)}`,
        { signal: controller.signal },
      ).then(setDatasetDetail).catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setActionError(error instanceof Error ? error.message : "تعذر تحميل تفاصيل Dataset.");
        }
      }).finally(() => {
        if (!controller.signal.aborted) setDatasetDetailLoading(false);
      });
    }, 0);
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [selectedDatasetKey]);

  const hasRunningRuns = data?.runs.some((run) => run.status === "running") ?? false;

  useEffect(() => {
    if (!hasRunningRuns) return;
    const interval = window.setInterval(() => {
      void fetchJson<EvaluationRun[]>("/api/evaluation/runs")
        .then((runs) => {
          setData((current) => current ? { ...current, runs } : current);
          if (selectedRun) {
            const updated = runs.find((run) => run.run_id === selectedRun.run_id);
            if (updated) setSelectedRun(updated);
          }
        })
        .catch(() => undefined);
    }, 2500);
    return () => window.clearInterval(interval);
  }, [hasRunningRuns, selectedRun]);

  const selectedDataset = useMemo(() => data?.datasets.find(
    (item) => `${item.name}::${item.version}` === selectedDatasetKey,
  ) ?? null, [data, selectedDatasetKey]);
  const selectedAgent = useMemo(() => data?.agents.find(
    (item) => `${item.tenant_id}::${item.id}` === selectedAgentKey,
  ) ?? null, [data, selectedAgentKey]);

  async function startRun(): Promise<void> {
    if (!selectedDataset || !selectedAgent) return;
    setStarting(true);
    setActionError(null);
    try {
      const run = await fetchJson<EvaluationRun>("/api/evaluation/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dataset_name: selectedDataset.name,
          dataset_version: selectedDataset.version,
          tenant_id: selectedAgent.tenant_id,
          agent_id: selectedAgent.id,
        }),
      });
      setData((current) => current ? {
        ...current,
        runs: [run, ...current.runs.filter((item) => item.run_id !== run.run_id)],
      } : current);
      setSelectedRun(run);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "تعذر بدء التشغيل.");
    } finally {
      setStarting(false);
    }
  }

  async function openRun(runId: string): Promise<void> {
    setActionError(null);
    try {
      setSelectedRun(await fetchJson<EvaluationRun>(
        `/api/evaluation/runs/${encodeURIComponent(runId)}`,
      ));
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "تعذر تحميل التشغيل.");
    }
  }

  if (loading && data === null) {
    return <main className={styles.page}><section className={styles.state}>
      <LoaderCircle className={styles.spinner} aria-hidden="true" />
      <h2>جاري تحميل مساحة التقييم</h2>
    </section></main>;
  }
  if (loadError && data === null) {
    return <main className={styles.page}><section className={styles.state}>
      <AlertTriangle aria-hidden="true" /><h2>{loadError}</h2>
      <button type="button" onClick={() => { setLoading(true); void loadDashboard(); }}>
        <RefreshCw aria-hidden="true" />إعادة المحاولة
      </button>
    </section></main>;
  }
  if (data === null) return null;

  const run = selectedRun;
  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <div>
          <span><FlaskConical aria-hidden="true" />Platform Evaluation</span>
          <h2>لوحة التقييم</h2>
          <p>شغّل Dataset مع وكيل حقيقي واستعرض النتائج المحفوظة دون مقاييس افتراضية.</p>
        </div>
        <button type="button" className={styles.refresh} onClick={() => void loadDashboard()}>
          <RefreshCw aria-hidden="true" />تحديث
        </button>
      </header>

      {actionError && <div className={styles.error} role="alert">
        <AlertTriangle aria-hidden="true" />{actionError}
      </div>}

      <section className={styles.launcher}>
        <div className={styles.sectionTitle}>
          <span><Play aria-hidden="true" /></span>
          <div><h3>تشغيل تقييم جديد</h3><p>يتم أخذ إعداد الوكيل ونسخة Prompt الحالية تلقائيًا.</p></div>
        </div>
        {data.datasets.length === 0 || data.agents.length === 0 ? (
          <div className={styles.empty}>
            <Database aria-hidden="true" />
            <p>{data.datasets.length === 0 ? "لا توجد Evaluation datasets متاحة." : "لا يوجد وكلاء نشطون للتقييم."}</p>
          </div>
        ) : (
          <div className={styles.formRow}>
            <label>Dataset
              <select value={selectedDatasetKey} onChange={(event) => setSelectedDatasetKey(event.target.value)}>
                {data.datasets.map((item) => <option key={`${item.name}::${item.version}`} value={`${item.name}::${item.version}`}>
                  {item.name} · {item.version} · {item.case_count} حالات
                </option>)}
              </select>
            </label>
            <label>الوكيل والإعداد
              <select value={selectedAgentKey} onChange={(event) => setSelectedAgentKey(event.target.value)}>
                {data.agents.map((item) => <option key={`${item.tenant_id}::${item.id}`} value={`${item.tenant_id}::${item.id}`}>
                  {item.name} · {item.tenant_name} · {item.knowledge_mode}
                </option>)}
              </select>
            </label>
            <button type="button" className={styles.start} disabled={starting} onClick={() => void startRun()}>
              {starting ? <LoaderCircle className={styles.spinner} aria-hidden="true" /> : <Play aria-hidden="true" />}
              {starting ? "جاري البدء" : "بدء التشغيل"}
            </button>
          </div>
        )}
        <div className={styles.datasetDetail}>
          {datasetDetailLoading ? <LoaderCircle className={styles.spinner} aria-label="جاري تحميل التفاصيل" /> : datasetDetail && (
            <><div><strong>{datasetDetail.name} · {datasetDetail.version}</strong><span>{datasetDetail.domain} · {datasetDetail.classification}</span></div>
            <div className={styles.tags}>{datasetDetail.records.slice(0, 8).map((item) => <span key={item.case_id}>{item.case_id}</span>)}
              {datasetDetail.records.length > 8 && <span>+{datasetDetail.records.length - 8}</span>}
            </div>
            <details className={styles.datasetCases}>
              <summary>عرض تفاصيل جميع الحالات ({datasetDetail.records.length})</summary>
              <div>{datasetDetail.records.map((item) => <article key={item.case_id}>
                <strong>{item.case_id}</strong>
                <p>{item.user_input}</p>
                <span>{item.category} · {item.difficulty} · {item.language ?? "—"}</span>
              </article>)}</div>
            </details></>
          )}
        </div>
      </section>

      <div className={styles.grid}>
        <section className={styles.history}>
          <div className={styles.sectionTitle}><span><Clock3 aria-hidden="true" /></span><div><h3>سجل التشغيلات</h3><p>{data.runs.length} تشغيل محفوظ</p></div></div>
          {data.runs.length === 0 ? <div className={styles.empty}><FlaskConical aria-hidden="true" /><p>لا توجد تشغيلات بعد.</p></div> : (
            <div className={styles.runList}>{data.runs.map((item) => (
              <button key={item.run_id} type="button" className={run?.run_id === item.run_id ? styles.runActive : styles.runItem} onClick={() => void openRun(item.run_id)}>
                <span className={runStatusClass(item.status)}>{statusIcon(item.status)}{statusLabel(item.status)}</span>
                <strong>{item.configuration.dataset_name} · {item.configuration.dataset_version}</strong>
                <small>{formatDate(item.started_at)}</small>
                <small>{item.summary.total_cases} حالات · {numberFormatter.format(item.summary.pass_rate_percent)}%</small>
              </button>
            ))}</div>
          )}
        </section>

        <section className={styles.detail}>
          {!run ? <div className={styles.empty}><FlaskConical aria-hidden="true" /><p>اختر تشغيلًا لعرض المقاييس والنتائج.</p></div> : <>
            <header className={styles.detailHeader}>
              <div><span className={runStatusClass(run.status)}>{statusIcon(run.status)}{statusLabel(run.status)}</span><h3>{run.configuration.dataset_name} · {run.configuration.dataset_version}</h3><code>{run.run_id}</code></div>
              <div className={styles.config}><span>Prompt: {run.configuration.prompt_version}</span><span>Model: {run.configuration.model_name}</span><span>Agent: {run.agent_id}</span></div>
            </header>
            {run.failure_reason && <div className={styles.error}>{run.failure_reason}</div>}
            <div className={styles.metrics}>
              <Metric label="إجمالي الحالات" value={run.summary.total_cases} />
              <Metric label="نسبة النجاح" value={`${numberFormatter.format(run.summary.pass_rate_percent)}%`} />
              <Metric label="متوسط الاستجابة" value={`${numberFormatter.format(run.summary.average_latency_ms)} ms`} />
              <Metric label="Failure rate" value={`${numberFormatter.format(run.summary.failure_rate_percent)}%`} />
              <Metric label="Retrieval hit rate" value={run.summary.retrieval_hit_rate_percent == null ? null : `${numberFormatter.format(run.summary.retrieval_hit_rate_percent)}%`} />
              <Metric label="Citation accuracy" value={run.summary.citation_accuracy_rate_percent == null ? null : `${numberFormatter.format(run.summary.citation_accuracy_rate_percent)}%`} />
              <Metric label="Prompt tokens" value={run.summary.total_prompt_tokens} />
              <Metric label="Completion tokens" value={run.summary.total_completion_tokens} />
            </div>
            {run.status === "running" && <div className={styles.runningNotice}><LoaderCircle className={styles.spinner} aria-hidden="true" />التشغيل جارٍ وسيتم تحديث النتائج تلقائيًا.</div>}
            <div className={styles.results}>
              <h4>نتائج الحالات</h4>
              {run.results.length === 0 ? <p className={styles.muted}>لا توجد نتائج متاحة بعد.</p> : run.results.map((result) => <CaseResultCard key={result.case_id} result={result} />)}
            </div>
          </>}
        </section>
      </div>
    </main>
  );
}
