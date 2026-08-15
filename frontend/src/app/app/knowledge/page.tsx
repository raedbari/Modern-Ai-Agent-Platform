import { BookOpenCheck, Clock } from "lucide-react";

export const metadata = {
  title: "قواعد المعرفة | بوابة العميل",
};

export default function KnowledgePage() {
  return (
    <div className="coming-soon-card">
      <div className="coming-soon-card__icon">
        <BookOpenCheck aria-hidden="true" />
      </div>
      <h2>إدارة قواعد المعرفة</h2>
      <p>
        ستتمكن قريباً من رفع الملفات والأسئلة الشائعة لتغذية وكلاء المحادثة ببيانات شركتك.
      </p>
      <div className="coming-soon-card__badge">
        <Clock aria-hidden="true" />
        <span>قريباً في المرحلة القادمة</span>
      </div>
    </div>
  );
}
