"use client";

import { useMemo, useState } from "react";
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

export function ChatbotWizard() {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [purpose, setPurpose] = useState("");
  const canContinue = useMemo(() => step !== 0 || name.trim().length >= 2, [name, step]);
  const current = STEPS[step];
  const CurrentIcon = current.icon;

  function goNext() {
    if (canContinue) setStep((value) => Math.min(value + 1, STEPS.length - 1));
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
                <button className={`${styles.stepButton} ${isActive ? styles.stepActive : ""} ${isDone ? styles.stepDone : ""}`} key={title} onClick={() => setStep(index)} type="button">
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

          <footer className={styles.actions}>
            <button className={styles.backButton} disabled={step === 0} onClick={goBack} type="button"><ArrowRight size={17} />السابق</button>
            <div className={styles.actionHint}>{step === 0 && !canContinue ? "اكتب اسمًا للـChatbot للمتابعة." : "يمكنك الرجوع وتعديل الإعدادات في أي وقت."}</div>
            <button className={styles.nextButton} disabled={!canContinue} onClick={goNext} type="button">{step === STEPS.length - 1 ? "إنهاء الإعداد" : "حفظ ومتابعة"}<ArrowLeft size={17} /></button>
          </footer>
        </section>
      </div>
    </main>
  );
}
