"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useRef, useState } from "react";

type Agent = { id: string; name: string };
type KnowledgeBase = { id: string; name: string; description: string; status: string; classification: string };
type Document = {
  id: string;
  original_filename: string;
  source_name: string;
  status: "pending" | "processing" | "ready" | "failed" | "archived";
  failure_reason: string | null;
  version_number: number;
  predecessor_id: string | null;
  superseded_by_id: string | null;
};
type DocumentJob = {
  job_id: string | null;
  document: Document;
  status: "pending" | "processing" | "succeeded" | "failed" | "duplicate";
  duplicate: boolean;
  last_error: string | null;
};

const terminalJobStatuses = new Set(["succeeded", "failed", "duplicate"]);
const statusLabels: Record<Document["status"], string> = {
  pending: "بانتظار المعالجة",
  processing: "قيد المعالجة",
  ready: "جاهز",
  failed: "فشل",
  archived: "مؤرشف",
};

async function responseDetail(response: Response, fallback: string): Promise<string> {
  const body = await response.json().catch(() => null) as { detail?: unknown } | null;
  return typeof body?.detail === "string" ? body.detail : fallback;
}

export function CustomerKnowledge() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [agentId, setAgentId] = useState("");
  const [knowledgeBaseId, setKnowledgeBaseId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const pollingController = useRef<AbortController | null>(null);

  const loadResources = useCallback(async () => {
    setError("");
    const [agentResponse, knowledgeResponse] = await Promise.all([
      fetch("/api/customer/agents", { cache: "no-store" }),
      fetch("/api/customer/knowledge-bases", { cache: "no-store" }),
    ]);
    if (!agentResponse.ok || !knowledgeResponse.ok) throw new Error("تعذر تحميل Chatbots أو قواعد المعرفة.");
    const nextAgents = await agentResponse.json() as Agent[];
    const nextKnowledgeBases = await knowledgeResponse.json() as KnowledgeBase[];
    setAgents(nextAgents);
    setKnowledgeBases(nextKnowledgeBases);
    setAgentId((current) => current || nextAgents[0]?.id || "");
    setKnowledgeBaseId((current) => current || nextKnowledgeBases[0]?.id || "");
  }, []);

  const loadDocuments = useCallback(async () => {
    if (!agentId || !knowledgeBaseId) { setDocuments([]); return; }
    const response = await fetch(
      `/api/customer/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents?agentId=${encodeURIComponent(agentId)}`,
      { cache: "no-store" },
    );
    if (response.status === 404) { setDocuments([]); return; }
    if (!response.ok) throw new Error(await responseDetail(response, "تعذر تحميل المستندات."));
    setDocuments(await response.json() as Document[]);
  }, [agentId, knowledgeBaseId]);

  useEffect(() => {
    let active = true;
    const timeout = window.setTimeout(() => {
      void loadResources()
        .catch((reason: unknown) => active && setError(reason instanceof Error ? reason.message : "تعذر تحميل البيانات."))
        .finally(() => active && setLoading(false));
    }, 0);
    return () => { active = false; window.clearTimeout(timeout); pollingController.current?.abort(); };
  }, [loadResources]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadDocuments().catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "تعذر تحميل المستندات."));
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [loadDocuments]);

  async function createKnowledgeBase(event: FormEvent) {
    event.preventDefault();
    if (!agentId || name.trim().length < 2) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch("/api/customer/knowledge-bases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agentId, name: name.trim(), description: description.trim() }),
      });
      if (!response.ok) throw new Error(await responseDetail(response, "تعذر إنشاء قاعدة المعرفة."));
      const created = await response.json() as KnowledgeBase;
      await loadResources();
      setKnowledgeBaseId(created.id); setName(""); setDescription("");
      setNotice("تم إنشاء قاعدة المعرفة وربطها بالـChatbot المحدد.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "تعذر إنشاء قاعدة المعرفة."); }
    finally { setBusy(false); }
  }

  async function assignKnowledgeBase() {
    if (!agentId || !knowledgeBaseId) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const response = await fetch(
        `/api/customer/agents/${encodeURIComponent(agentId)}/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}`,
        { method: "PUT" },
      );
      if (!response.ok) throw new Error(await responseDetail(response, "تعذر ربط قاعدة المعرفة."));
      setNotice("تم ربط قاعدة المعرفة بالـChatbot. العملية آمنة عند التكرار.");
      await loadDocuments();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "تعذر ربط قاعدة المعرفة."); }
    finally { setBusy(false); }
  }

  async function pollJob(jobId: string) {
    pollingController.current?.abort();
    const controller = new AbortController();
    pollingController.current = controller;
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise<void>((resolve) => window.setTimeout(resolve, 2000));
      if (controller.signal.aborted) return;
      const response = await fetch(
        `/api/customer/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/jobs/${encodeURIComponent(jobId)}?agentId=${encodeURIComponent(agentId)}`,
        { cache: "no-store", signal: controller.signal },
      );
      if (!response.ok) throw new Error(await responseDetail(response, "تعذر متابعة معالجة المستند."));
      const job = await response.json() as DocumentJob;
      if (terminalJobStatuses.has(job.status)) {
        await loadDocuments();
        if (job.status === "failed") throw new Error(job.last_error || "فشلت معالجة المستند.");
        setNotice(job.duplicate ? "المستند مكرر؛ لم يتم إنشاء نسخة إضافية." : "اكتملت معالجة المستند.");
        return;
      }
      await loadDocuments();
    }
    throw new Error("استمرت المعالجة أكثر من دقيقتين. يمكنك تحديث الصفحة لمراجعة الحالة لاحقًا.");
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; event.target.value = "";
    if (!file || !agentId || !knowledgeBaseId) return;
    setBusy(true); setError(""); setNotice("تم رفع الملف وبدأت المعالجة في الخلفية.");
    try {
      const form = new FormData(); form.set("file", file); form.set("source_name", file.name);
      const response = await fetch(
        `/api/customer/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents?agentId=${encodeURIComponent(agentId)}`,
        { method: "POST", body: form },
      );
      if (!response.ok) throw new Error(await responseDetail(response, "تعذر رفع المستند."));
      const job = await response.json() as DocumentJob;
      await loadDocuments();
      if (job.duplicate || job.status === "duplicate") setNotice("المستند مكرر؛ لم يتم إنشاء نسخة إضافية.");
      else if (job.job_id) await pollJob(job.job_id);
    } catch (reason) {
      if (!(reason instanceof DOMException && reason.name === "AbortError")) setError(reason instanceof Error ? reason.message : "تعذر معالجة المستند.");
    } finally { setBusy(false); }
  }

  async function mutateDocument(document: Document, action: "archive" | "delete", replacement?: File) {
    if (!agentId || !knowledgeBaseId) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const queryAction = replacement ? "&action=replace" : action === "archive" ? "&action=archive" : "";
      const form = replacement ? new FormData() : undefined;
      if (form && replacement) { form.set("file", replacement); form.set("source_name", replacement.name); }
      const response = await fetch(
        `/api/customer/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents/${encodeURIComponent(document.id)}?agentId=${encodeURIComponent(agentId)}${queryAction}`,
        { method: action === "delete" ? "DELETE" : "POST", body: form },
      );
      if (!response.ok) throw new Error(await responseDetail(response, "تعذر تحديث المستند."));
      await loadDocuments();
      setNotice(replacement ? "اكتمل الاستبدال المتزامن وأنشئت نسخة جديدة من المستند." : action === "archive" ? "تمت أرشفة المستند." : "تم حذف المستند.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "تعذر تحديث المستند."); }
    finally { setBusy(false); }
  }

  if (loading) return <div className="coming-soon-card"><p>جاري تحميل قواعد المعرفة…</p></div>;

  return <main className="dashboard-placeholder" dir="rtl">
    <header className="dashboard-placeholder__header"><div><h1>قواعد المعرفة</h1><p>المصدر الفعلي للمستندات وحالات المعالجة</p></div></header>
    {error ? <p role="alert">{error}</p> : null}{notice ? <p role="status">{notice}</p> : null}
    {agents.length === 0 ? <section className="coming-soon-card"><p>أنشئ Chatbot أولًا قبل إضافة المعرفة.</p></section> : <>
      <section className="coming-soon-card"><h2>اختيار وربط قاعدة معرفة</h2>
        <label>Chatbot<select value={agentId} onChange={(event) => setAgentId(event.target.value)}>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}</select></label>
        <label>قاعدة موجودة<select value={knowledgeBaseId} onChange={(event) => setKnowledgeBaseId(event.target.value)}><option value="">اختر قاعدة معرفة</option>{knowledgeBases.map((item) => <option key={item.id} value={item.id}>{item.name} — {item.status}</option>)}</select></label>
        <button type="button" disabled={busy || !knowledgeBaseId} onClick={() => void assignKnowledgeBase()}>ربط القاعدة المحددة</button>
      </section>
      <form className="coming-soon-card" onSubmit={(event) => void createKnowledgeBase(event)}><h2>قاعدة معرفة جديدة</h2>
        <label>الاسم<input value={name} onChange={(event) => setName(event.target.value)} /></label>
        <label>الوصف<textarea value={description} onChange={(event) => setDescription(event.target.value)} /></label>
        <button type="submit" disabled={busy || name.trim().length < 2}>إنشاء وربط</button>
      </form>
      <section className="coming-soon-card"><h2>المستندات</h2>
        <label>رفع مستند للمعالجة غير المتزامنة<input type="file" disabled={busy || !knowledgeBaseId} onChange={(event) => void upload(event)} /></label>
        {documents.length === 0 ? <p>لا توجد مستندات محفوظة لهذا الاختيار.</p> : documents.map((document) => <article key={document.id}>
          <h3>{document.original_filename}</h3><p>{statusLabels[document.status]} · الإصدار {document.version_number}{document.predecessor_id ? " · نسخة بديلة" : ""}{document.superseded_by_id ? " · تم استبداله" : ""}</p>
          {document.failure_reason ? <p role="alert">{document.failure_reason}</p> : null}
          <button type="button" disabled={busy || document.status === "archived"} onClick={() => void mutateDocument(document, "archive")}>أرشفة</button>{" "}
          <button type="button" disabled={busy} onClick={() => { if (window.confirm("حذف المستند نهائيًا؟")) void mutateDocument(document, "delete"); }}>حذف</button>{" "}
          <label>استبدال متزامن<input type="file" disabled={busy} onChange={(event) => { const replacement = event.target.files?.[0]; event.target.value = ""; if (replacement) void mutateDocument(document, "archive", replacement); }} /></label>
        </article>)}
      </section>
    </>}
  </main>;
}
