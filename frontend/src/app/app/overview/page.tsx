import Link from "next/link";
import {
  ArrowLeft,
  BookOpenCheck,
  Bot,
  MessageSquareText,
  Sparkles,
} from "lucide-react";

export const metadata = {
  title: "نظرة عامة | بوابة العميل",
};

export default function TenantOverviewPage() {
  return (
    <div className="tenant-overview">
      <div className="tenant-overview__welcome">
        <div className="tenant-overview__welcome-content">
          <div className="tenant-overview__badge">
            <Sparkles aria-hidden="true" />
            <span>مرحباً بك في Athkachatbots</span>
          </div>
          <h1>مساحة عملك جاهزة لخدمة عملائك بأذكى الطرق</h1>
          <p>
            يمكنك الآن إنشاء وكلاء المحادثة، ربط مصادر المعرفة، ومتابعة المحادثات
            المباشرة من مكان واحد.
          </p>
        </div>
      </div>

      <div className="tenant-overview__stats">
        <div className="tenant-stat-card">
          <div className="tenant-stat-card__icon tenant-stat-card__icon--bot">
            <Bot aria-hidden="true" />
          </div>
          <div className="tenant-stat-card__info">
            <span>الوكلاء الذكية</span>
            <strong>0 وكيل</strong>
          </div>
          <Link href="/app/chatbots" className="tenant-stat-card__link">
            <span>إدارة الوكلاء</span>
            <ArrowLeft aria-hidden="true" />
          </Link>
        </div>

        <div className="tenant-stat-card">
          <div className="tenant-stat-card__icon tenant-stat-card__icon--knowledge">
            <BookOpenCheck aria-hidden="true" />
          </div>
          <div className="tenant-stat-card__info">
            <span>قواعد المعرفة</span>
            <strong>0 مستند</strong>
          </div>
          <Link href="/app/knowledge" className="tenant-stat-card__link">
            <span>إدارة المعرفة</span>
            <ArrowLeft aria-hidden="true" />
          </Link>
        </div>

        <div className="tenant-stat-card">
          <div className="tenant-stat-card__icon tenant-stat-card__icon--conversations">
            <MessageSquareText aria-hidden="true" />
          </div>
          <div className="tenant-stat-card__info">
            <span>المحادثات النشطة</span>
            <strong>0 محادثة</strong>
          </div>
          <Link href="/app/conversations" className="tenant-stat-card__link">
            <span>سجل المحادثات</span>
            <ArrowLeft aria-hidden="true" />
          </Link>
        </div>
      </div>

      <div className="tenant-overview__phase-notice">
        <h3>مرحلة الإطلاق التجريبي (Phase 1)</h3>
        <p>
          نحن نعمل باستمرار على إضافة ميزات جديدة إلى لوحة التحكم الخاصة بك. في
          حال احتجت إلى أي مساعدة، فريق الدعم الفني متواجد لمساعدتك.
        </p>
      </div>
    </div>
  );
}
