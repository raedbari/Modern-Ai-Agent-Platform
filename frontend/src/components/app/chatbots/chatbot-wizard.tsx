"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Bot, BookOpen, Check, Code2, MessageSquareText, Palette, Play, Rocket, Sparkles } from "lucide-react";
import styles from "./chatbot-wizard.module.css";

const STEPS = [
  { title: "المعلومات", description: "اسم Chatbot والهدف الأساسي منه.", icon: Bot },
  { title: "المعرفة", description: "المصادر التي سيعتمد عليها Chatbot.", icon: BookOpen },
  { title: "طريقة الرد", description: "النبرة والتعليمات وطريقة التعامل مع الأسئلة.", icon: MessageSquareText },
  { title: "المظهر", description: "الاسم والألوان ورسالة الترحيب.", icon: Palette },
  { title: "التجربة", description: "اختبر Chatbot قبل نشره.", icon: Play },
  { title: "النشر", description: "راجع الإعدادات واجعل Chatbot جاهزًا.", icon: Rocket },
  { title: "الدمج", description: "أضف Chatbot إلى موقعك بخطوات بسيطة.", icon: Code2 },
];

type WizardDraft = {
  agentId: string | null;
  name: string;
  purpose: string;
  step: number;
};

type CustomerAgentResponse = {
  id: string;
  name: string;
};

const WIZARD_STORAGE_KEY =
  "athka-chatbot-wizard-v1";

function apiErrorMessage(
  payload: unknown,
  status: number,
): string {
  if (
    payload !== null &&
    typeof payload === "object" &&
    "detail" in payload
  ) {
    const detail =
      (payload as {
        detail?: unknown;
      }).detail;

    if (
      typeof detail === "string" &&
      detail.trim()
    ) {
      return detail;
    }
  }

  if (status === 401) {
    return "\u0627\u0646\u062a\u0647\u062a \u0627\u0644\u062c\u0644\u0633\u0629. \u0633\u062c\u0644 \u0627\u0644\u062f\u062e\u0648\u0644 \u0645\u0646 \u062c\u062f\u064a\u062f.";
  }

  return "\u062a\u0639\u0630\u0631 \u062d\u0641\u0638 Chatbot. \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.";
}

export function ChatbotWizard() {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [purpose, setPurpose] = useState("");
  const [agentId, setAgentId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  const canContinue = useMemo(
    () =>
      step !== 0 ||
      name.trim().length >= 2,
    [name, step],
  );
  const current = STEPS[step];
  const CurrentIcon = current.icon;

  useEffect(() => {
    const raw =
      window.sessionStorage.getItem(
        WIZARD_STORAGE_KEY,
      );

    queueMicrotask(() => {
      if (!raw) {
        setHydrated(true);
        return;
      }

      try {
        const draft =
          JSON.parse(raw) as Partial<WizardDraft>;

        const restoredAgentId =
          typeof draft.agentId === "string" &&
          draft.agentId
            ? draft.agentId
            : null;

        if (
          typeof draft.name === "string"
        ) {
          setName(draft.name);
        }

        if (
          typeof draft.purpose === "string"
        ) {
          setPurpose(draft.purpose);
        }

        setAgentId(
          restoredAgentId,
        );

        if (
          restoredAgentId &&
          typeof draft.step === "number"
        ) {
          setStep(
            Math.min(
              Math.max(
                Math.trunc(draft.step),
                0,
              ),
              STEPS.length - 1,
            ),
          );
        }
      } catch {
        window.sessionStorage.removeItem(
          WIZARD_STORAGE_KEY,
        );
      }

      setHydrated(true);
    });
  }, []);

  useEffect(() => {
    if (!hydrated) {
      return;
    }

    const draft: WizardDraft = {
      agentId,
      name,
      purpose,
      step,
    };

    window.sessionStorage.setItem(
      WIZARD_STORAGE_KEY,
      JSON.stringify(draft),
    );
  }, [
    agentId,
    hydrated,
    name,
    purpose,
    step,
  ]);

  async function goNext(): Promise<void> {
    if (
      !canContinue ||
      saving
    ) {
      return;
    }

    if (step !== 0) {
      setStep((value) =>
        Math.min(
          value + 1,
          STEPS.length - 1,
        ),
      );
      return;
    }

    setSaving(true);
    setSaveError(null);

    try {
      const endpoint = agentId
        ? `/api/customer/agents/${
            encodeURIComponent(agentId)
          }`
        : "/api/customer/agents";

      const response = await fetch(
        endpoint,
        {
          method:
            agentId
              ? "PATCH"
              : "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            Accept:
              "application/json",
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            name: name.trim(),
          }),
        },
      );

      let body: unknown;

      try {
        body =
          await response.json();
      } catch {
        body = undefined;
      }

      if (!response.ok) {
        throw new Error(
          apiErrorMessage(
            body,
            response.status,
          ),
        );
      }

      if (
        body === null ||
        typeof body !== "object" ||
        !("id" in body) ||
        typeof (
          body as CustomerAgentResponse
        ).id !== "string"
      ) {
        throw new Error(
          "\u062a\u0639\u0630\u0631 \u062d\u0641\u0638 Chatbot. \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.",
        );
      }

      const agent =
        body as CustomerAgentResponse;

      setAgentId(
        agent.id,
      );

      if (
        typeof agent.name === "string"
      ) {
        setName(
          agent.name,
        );
      }

      setStep(1);
    } catch (error) {
      setSaveError(
        error instanceof Error
          ? error.message
          : "\u062a\u0639\u0630\u0631 \u062d\u0641\u0638 Chatbot. \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.",
      );
    } finally {
      setSaving(false);
    }
  }

  function goBack() {
    setStep((value) => Math.max(value - 1, 0));
  }

  return (
    <main className={styles.page} dir="rtl">
      <div className={styles.topBar}>
        <div>
          <div className={styles.eyebrow}><Sparkles size={15} />إنشاء Chatbot</div>
          <h1>أنشئ Chatbot خطوة بخطوة</h1>
          <p>إعداد سريع ومرئي بدون شاشات معقدة.</p>
        </div>
        <Link className={styles.closeLink} href="/app/chatbots">العودة إلى Chatbots</Link>
      </div>

      <div className={styles.layout}>
        <aside className={styles.stepsPanel}>
          <div className={styles.progressText}>الخطوة {step + 1} من {STEPS.length}</div>
          <div className={styles.progressTrack}><span style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} /></div>
          <nav className={styles.steps}>
            {STEPS.map(({ title, icon: Icon }, index) => {
              const isActive = index === step;
              const isDone = index < step;
              return (
                <button className={`${styles.stepButton} ${isActive ? styles.stepActive : ""} ${isDone ? styles.stepDone : ""}`} key={title} disabled={index > 0 && !agentId} onClick={() => {
                    if (index === 0 || agentId) setStep(index);
                  }} type="button">
                  <span className={styles.stepIcon}>{isDone ? <Check size={16} /> : <Icon size={16} />}</span>
                  <span><strong>{title}</strong><small>{STEPS[index].description}</small></span>
                </button>
              );
            })}
          </nav>
        </aside>

        <section className={styles.stage}>
          <div className={styles.stageHeader}>
            <div className={styles.stageIcon}><CurrentIcon size={24} /></div>
            <div><span>الخطوة {step + 1}</span><h2>{current.title}</h2><p>{current.description}</p></div>
          </div>

          {step === 0 ? (
            <div className={styles.form}>
              <label className={styles.field}>
                <span>اسم Chatbot</span>
                <input autoFocus onChange={(event) => setName(event.target.value)} placeholder="مثال: مساعد TravelX" value={name} />
                <small>هذا الاسم سيظهر لك داخل المنصة ويمكن تغييره لاحقًا.</small>
              </label>
              <label className={styles.field}>
                <span>ما الهدف من Chatbot؟</span>
                <textarea onChange={(event) => setPurpose(event.target.value)} placeholder="مثال: الرد على أسئلة العملاء ومساعدتهم في معرفة الخدمات." rows={5} value={purpose} />
                <small>اكتب وصفًا بسيطًا. سنستخدمه لاحقًا عند إعداد طريقة الرد.</small>
              </label>
            </div>
          ) : (
            <div className={styles.placeholder}>
              <div className={styles.placeholderIcon}><CurrentIcon size={30} /></div>
              <h3>{current.title}</h3>
              <p>واجهة هذه الخطوة جاهزة ضمن مسار الـWizard، وسيتم ربطها بخدمات المنصة الحالية في الوحدة التالية.</p>
            </div>
          )}

          {saveError ? (
            <p
              className={styles.actionError}
              role="alert"
            >
              {saveError}
            </p>
          ) : null}

          <footer className={styles.actions}>
            <button className={styles.backButton} disabled={step === 0} onClick={goBack} type="button"><ArrowRight size={17} />السابق</button>
            <div className={styles.actionHint}>{step === 0 && !canContinue ? "اكتب اسمًا للـChatbot للمتابعة." : "يمكنك الرجوع وتعديل الإعدادات في أي وقت."}</div>
            {saving ? (
              <span className={styles.savingNote}>
                {"جاري الحفظ…"}
              </span>
            ) : null}
            <button className={styles.nextButton} disabled={!canContinue || saving} onClick={() => { void goNext(); }} type="button">{step === STEPS.length - 1 ? "إنهاء الإعداد" : "حفظ ومتابعة"}<ArrowLeft size={17} /></button>
          </footer>
        </section>
      </div>
    </main>
  );
}
