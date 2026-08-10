import Link from "next/link";
import { Bot, BookOpen, Code2, MessageSquareText, Palette, Play, Plus, Rocket, Sparkles } from "lucide-react";
import styles from "./chatbots.module.css";

const FLOW = [
  { label: "المعلومات", icon: Bot },
  { label: "المعرفة", icon: BookOpen },
  { label: "طريقة الرد", icon: MessageSquareText },
  { label: "المظهر", icon: Palette },
  { label: "التجربة", icon: Play },
  { label: "النشر", icon: Rocket },
  { label: "الدمج", icon: Code2 },
];

export default function ChatbotsPage() {
  return (
    <main className={styles.page} dir="rtl">
      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <div className={styles.eyebrow}><Sparkles size={16} />Chatbots الخاصة بك</div>
          <h1>أنشئ وكيلك الذكي بخطوات بسيطة</h1>
          <p>ابدأ بإنشاء Chatbot جديد، ثم أضف المعرفة واضبط طريقة الرد والمظهر واختبره قبل نشره ودمجه في موقعك.</p>
        </div>
        <Link className={styles.primaryButton} href="/app/chatbots/new"><Plus size={18} />إنشاء Chatbot</Link>
      </section>

      <section className={styles.emptyState}>
        <div className={styles.emptyIcon}><Bot size={36} /></div>
        <h2>لا يوجد Chatbot بعد</h2>
        <p>أنشئ أول Chatbot عبر معالج مرئي وسريع. ستنتقل خطوة بخطوة من المعلومات الأساسية حتى الدمج في موقعك.</p>
        <div className={styles.flow} aria-label="خطوات إنشاء Chatbot">
          {FLOW.map(({ label, icon: Icon }, index) => (
            <div className={styles.flowItem} key={label}>
              <span className={styles.flowNumber}>{index + 1}</span><Icon size={16} /><span>{label}</span>
            </div>
          ))}
        </div>
        <Link className={styles.secondaryButton} href="/app/chatbots/new"><Plus size={17} />ابدأ إنشاء Chatbot</Link>
      </section>
    </main>
  );
}
