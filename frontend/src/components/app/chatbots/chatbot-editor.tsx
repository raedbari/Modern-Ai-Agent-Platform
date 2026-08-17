"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

type Agent = { id: string; name: string; system_prompt: string | null; knowledge_mode: "required" | "preferred" | "disabled"; contact_message: string | null };
type Source = { citation_id: string; source_name: string; page_number: number };
type Widget = { public_widget_id: string; is_enabled: boolean; display_name: string | null; greeting: string | null; primary_color: string; text_color: string; launcher_color: string; header_color: string; user_message_color: string; position: "left" | "right"; appearance: "light" | "dark"; allowed_origins: string[] };

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000").replace(/\/+$/, "");
const WIDGET_SCRIPT = process.env.NEXT_PUBLIC_WIDGET_URL ?? "https://cdn.travel-x.online/widget/v1.js";

export function ChatbotEditor({ agentId }: { agentId: string }) {
  const [agent, setAgent] = useState<Agent | null>(null); const [error, setError] = useState(""); const [notice, setNotice] = useState("");
  const [message, setMessage] = useState(""); const [reply, setReply] = useState(""); const [answerStatus, setAnswerStatus] = useState(""); const [sources, setSources] = useState<Source[]>([]); const conversation = useRef<string | undefined>(undefined);
  const [widget, setWidget] = useState<Widget | null>(null); const [origins, setOrigins] = useState(""); const [previewToken, setPreviewToken] = useState(""); const [previewMessage, setPreviewMessage] = useState(""); const [previewReply, setPreviewReply] = useState(""); const [pairing, setPairing] = useState("");

  const load = useCallback(async () => {
    try {
      setError("");
      const agentResponse = await fetch(`/api/customer/agents/${encodeURIComponent(agentId)}`, { cache: "no-store" });
      if (!agentResponse.ok) { setError("تعذر تحميل Chatbot."); return; }
      setAgent(await agentResponse.json() as Agent);
      const widgetResponse = await fetch(`/api/customer/agents/${encodeURIComponent(agentId)}/widget-settings`, { cache: "no-store" });
      if (widgetResponse.ok) { const value = await widgetResponse.json() as Widget; setWidget(value); setOrigins(value.allowed_origins.join("\n")); }
      else if (widgetResponse.status === 404) setWidget({ public_widget_id: "", is_enabled: false, display_name: null, greeting: null, primary_color: "#2563EB", text_color: "#FFFFFF", launcher_color: "#2563EB", header_color: "#2563EB", user_message_color: "#2563EB", position: "right", appearance: "light", allowed_origins: [] });
      else setError("تعذر تحميل إعدادات Widget.");
    } catch { setError("تعذر الاتصال بالخدمة."); }
  }, [agentId]);
  useEffect(() => {
    const timeout = window.setTimeout(() => { void load(); }, 0);
    return () => window.clearTimeout(timeout);
  }, [load]);

  async function saveAgent(event: FormEvent) { event.preventDefault(); if (!agent) return; setNotice("");
    const response = await fetch(`/api/customer/agents/${encodeURIComponent(agentId)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: agent.name, system_prompt: agent.system_prompt, knowledge_mode: agent.knowledge_mode, contact_message: agent.contact_message }) });
    if (!response.ok) { setError("تعذر حفظ إعدادات Chatbot."); return; } setAgent(await response.json() as Agent); setNotice("تم حفظ إعدادات Chatbot.");
  }
  async function testRag(event: FormEvent) { event.preventDefault(); if (!message.trim()) return;
    const response = await fetch("/api/customer/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ agentId, message, conversation_id: conversation.current }) });
    const body = await response.json().catch(() => null) as { conversation_id?: string; reply?: string; answer_status?: string; sources?: Source[]; detail?: string } | null;
    if (!response.ok) { setError(body?.detail ?? "تعذر اختبار RAG."); return; } conversation.current = body?.conversation_id; setReply(body?.reply ?? ""); setAnswerStatus(body?.answer_status ?? ""); setSources(body?.sources ?? []);
  }
  async function saveWidget(enable?: boolean): Promise<boolean> { const current = widget ?? { public_widget_id: "", is_enabled: false, display_name: agent?.name ?? null, greeting: null, primary_color: "#2563EB", text_color: "#FFFFFF", launcher_color: "#2563EB", header_color: "#2563EB", user_message_color: "#2563EB", position: "right" as const, appearance: "light" as const, allowed_origins: [] };
    const payload = { is_enabled: enable ?? current.is_enabled, display_name: current.display_name, greeting: current.greeting, primary_color: current.primary_color, text_color: current.text_color, launcher_color: current.launcher_color, header_color: current.header_color, user_message_color: current.user_message_color, position: current.position, appearance: current.appearance, allowed_origins: origins.split(/\r?\n/).map((value) => value.trim()).filter(Boolean) };
    if (payload.is_enabled && payload.allowed_origins.length === 0) { setError("أضف نطاقًا مسموحًا قبل النشر."); return false; }
    const response = await fetch(`/api/customer/agents/${encodeURIComponent(agentId)}/widget-settings`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!response.ok) { setError("تعذر حفظ إعدادات Widget."); return false; } const saved = await response.json() as Widget; setWidget(saved); setOrigins(saved.allowed_origins.join("\n")); setNotice(saved.is_enabled ? "تم نشر Widget." : "تم حفظ Widget دون نشر."); return true;
  }
  async function preview() { if (!widget?.public_widget_id && !(await saveWidget(false))) return;
    const response = await fetch(`/api/customer/agents/${encodeURIComponent(agentId)}/widget-settings/preview`, { method: "POST" }); const body = await response.json().catch(() => null) as { session_token?: string; detail?: string } | null;
    if (!response.ok || !body?.session_token) { setError(body?.detail ?? "تعذر بدء المعاينة."); return; } setPreviewToken(body.session_token); setNotice("المعاينة الحقيقية جاهزة.");
  }
  async function sendPreview(event: FormEvent) { event.preventDefault(); if (!previewToken || !previewMessage.trim()) return;
    const response = await fetch(`${API_BASE}/api/chat`, { method: "POST", headers: { Authorization: `Bearer ${previewToken}`, "Content-Type": "application/json" }, body: JSON.stringify({ message: previewMessage }) }); const body = await response.json().catch(() => null) as { reply?: string; detail?: string } | null; setPreviewReply(response.ok ? body?.reply ?? "" : body?.detail ?? "تعذر إرسال رسالة المعاينة.");
  }
  async function createPairing() { const origin = origins.split(/\r?\n/).map((v) => v.trim()).find(Boolean); if (!origin) { setError("أضف نطاقًا مسموحًا أولًا."); return; }
    const response = await fetch(`/api/customer/agents/${encodeURIComponent(agentId)}/widget-settings/pairings`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ origin, connector_type: "custom" }) }); const body = await response.json().catch(() => null) as { pairing_code?: string; detail?: string } | null; if (!response.ok) { setError(body?.detail ?? "تعذر إنشاء رمز الربط."); return; } setPairing(body?.pairing_code ?? "");
  }
  async function copyText(value: string, success: string) {
    try { await navigator.clipboard.writeText(value); setNotice(success); setError(""); }
    catch { setError("تعذر النسخ إلى الحافظة."); }
  }
  const embed = useMemo(() => widget?.public_widget_id ? `<script>window.WidgetConfig={widgetId:"${widget.public_widget_id}",apiBaseUrl:"${API_BASE}",language:"ar",direction:"rtl"};</script>\n<script src="${WIDGET_SCRIPT}" defer></script>` : "", [widget]);

  if (!agent) return <main className="dashboard-placeholder" dir="rtl"><p>{error || "جاري التحميل…"}</p></main>;
  return <main className="dashboard-placeholder" dir="rtl"><header className="dashboard-placeholder__header"><div><h1>{agent.name}</h1><p>التكوين والاختبار والنشر</p></div><Link href="/app/chatbots">العودة</Link></header>{error ? <p role="alert">{error}</p> : null}{notice ? <p role="status">{notice}</p> : null}
    <form className="coming-soon-card" onSubmit={(e) => void saveAgent(e)}><h2>إعداد Chatbot</h2><label>الاسم<input value={agent.name} onChange={(e) => setAgent({ ...agent, name: e.target.value })} /></label><label>System prompt<textarea rows={7} value={agent.system_prompt ?? ""} onChange={(e) => setAgent({ ...agent, system_prompt: e.target.value || null })} /></label><label>وضع المعرفة<select value={agent.knowledge_mode} onChange={(e) => setAgent({ ...agent, knowledge_mode: e.target.value as Agent["knowledge_mode"] })}><option value="required">مطلوبة</option><option value="preferred">مفضلة</option><option value="disabled">معطلة</option></select></label><label>رسالة عدم توفر المعرفة<textarea value={agent.contact_message ?? ""} onChange={(e) => setAgent({ ...agent, contact_message: e.target.value || null })} /></label><button type="submit">حفظ</button></form>
    <form className="coming-soon-card" onSubmit={(e) => void testRag(e)}><h2>اختبار RAG الحقيقي</h2><textarea value={message} onChange={(e) => setMessage(e.target.value)} /><button type="submit">إرسال</button><button type="button" onClick={() => { conversation.current = undefined; setReply(""); setAnswerStatus(""); setSources([]); }}>محادثة جديدة</button>{reply ? <div><strong>{answerStatus}</strong><p>{reply}</p>{sources.map((s) => <p key={s.citation_id}>[{s.citation_id}] {s.source_name} — صفحة {s.page_number}</p>)}</div> : null}</form>
    <section className="coming-soon-card"><h2>Widget والموقع</h2><label>اسم العرض<input value={widget?.display_name ?? ""} onChange={(e) => widget && setWidget({ ...widget, display_name: e.target.value || null })} /></label><label>رسالة الترحيب<textarea value={widget?.greeting ?? ""} onChange={(e) => widget && setWidget({ ...widget, greeting: e.target.value || null })} /></label>
      <label>اللون الأساسي<input type="color" value={widget?.primary_color ?? "#2563EB"} onChange={(e) => widget && setWidget({ ...widget, primary_color: e.target.value })} /></label><label>لون النص<input type="color" value={widget?.text_color ?? "#FFFFFF"} onChange={(e) => widget && setWidget({ ...widget, text_color: e.target.value })} /></label><label>لون المشغّل<input type="color" value={widget?.launcher_color ?? "#2563EB"} onChange={(e) => widget && setWidget({ ...widget, launcher_color: e.target.value })} /></label><label>لون الرأس<input type="color" value={widget?.header_color ?? "#2563EB"} onChange={(e) => widget && setWidget({ ...widget, header_color: e.target.value })} /></label><label>لون رسالة المستخدم<input type="color" value={widget?.user_message_color ?? "#2563EB"} onChange={(e) => widget && setWidget({ ...widget, user_message_color: e.target.value })} /></label>
      <label>موضع المشغّل<select value={widget?.position ?? "right"} onChange={(e) => widget && setWidget({ ...widget, position: e.target.value as Widget["position"] })}><option value="right">يمين</option><option value="left">يسار</option></select></label><label>المظهر<select value={widget?.appearance ?? "light"} onChange={(e) => widget && setWidget({ ...widget, appearance: e.target.value as Widget["appearance"] })}><option value="light">فاتح</option><option value="dark">داكن</option></select></label>
      <label>النطاقات المسموحة — نطاق كامل في كل سطر<textarea rows={4} value={origins} onChange={(e) => setOrigins(e.target.value)} placeholder="https://example.com" /></label><button type="button" onClick={() => void saveWidget(false)}>حفظ دون نشر</button> <button type="button" onClick={() => void preview()}>بدء معاينة حقيقية</button> <button type="button" onClick={() => void saveWidget(true)}>نشر/تفعيل</button>
      {previewToken ? <form onSubmit={(e) => void sendPreview(e)}><input value={previewMessage} onChange={(e) => setPreviewMessage(e.target.value)} placeholder="رسالة المعاينة" /><button type="submit">اختبر Widget</button><p>{previewReply}</p></form> : null}
      {embed ? <><h3>كود الدمج</h3><textarea readOnly rows={5} value={embed} /><button type="button" onClick={() => void copyText(embed, "تم نسخ كود الدمج.")}>نسخ</button></> : null}
      <h3>Connector</h3><button type="button" disabled={!widget?.is_enabled} onClick={() => void createPairing()}>إنشاء رمز ربط</button>{pairing ? <p><strong>{pairing}</strong> — صالح لعشر دقائق ويُستخدم مرة واحدة. <button type="button" onClick={() => void copyText(pairing, "تم نسخ رمز الربط.")}>نسخ الرمز</button></p> : null}
    </section><p><Link href="/app/knowledge">إدارة قواعد المعرفة والمستندات</Link> · <Link href="/app/conversations">عرض المحادثات</Link></p></main>;
}
