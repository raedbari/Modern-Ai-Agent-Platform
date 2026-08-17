"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type Agent = { id: string; name: string; is_active: boolean; knowledge_mode: string };

export function CustomerChatbots() {
  const [items, setItems] = useState<Agent[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setStatus("loading"); setError("");
    const response = await fetch("/api/customer/agents", { cache: "no-store" });
    if (!response.ok) { setError("تعذر تحميل Chatbots."); setStatus("error"); return; }
    setItems(await response.json() as Agent[]); setStatus("ready");
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => { void load(); }, 0);
    return () => window.clearTimeout(timeout);
  }, [load]);

  async function remove(item: Agent) {
    if (!window.confirm(`حذف ${item.name} نهائيًا؟`)) return;
    const response = await fetch(`/api/customer/agents/${encodeURIComponent(item.id)}`, { method: "DELETE" });
    if (!response.ok) { setError("تعذر حذف Chatbot. قد تكون له موارد مرتبطة."); return; }
    await load();
  }

  return (
    <main className="dashboard-placeholder" dir="rtl">
      <header className="dashboard-placeholder__header">
        <div><h1>Chatbots الخاصة بك</h1><p>إدارة التعليمات والمعرفة والاختبار والنشر من بيانات المنصة الحقيقية.</p></div>
        <Link href="/app/chatbots/new">إنشاء Chatbot</Link>
      </header>
      {status === "loading" ? <p>جاري التحميل…</p> : null}
      {status === "error" ? <button onClick={() => void load()} type="button">إعادة المحاولة</button> : null}
      {error ? <p role="alert">{error}</p> : null}
      {status === "ready" && items.length === 0 ? <div className="coming-soon-card"><h2>لا يوجد Chatbot بعد</h2><Link href="/app/chatbots/new">أنشئ أول Chatbot</Link></div> : null}
      <div className="dashboard-placeholder__items">
        {items.map((item) => (
          <article key={item.id} className="coming-soon-card">
            <h2>{item.name}</h2><p>وضع المعرفة: {item.knowledge_mode}</p>
            <div><Link href={`/app/chatbots/${encodeURIComponent(item.id)}`}>فتح وإدارة</Link>{" "}<button onClick={() => void remove(item)} type="button">حذف</button></div>
          </article>
        ))}
      </div>
    </main>
  );
}
