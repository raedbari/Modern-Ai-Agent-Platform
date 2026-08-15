import type { ApplicationStatus } from "@/lib/server/tenant-auth-api";

export type StatusCopy = {
  title: string;
  description: string;
  iconName: string; // Lucide icon name
  actionLabel: string | null;
  actionHref: string | null;
};

export const APPLICATION_STATUS_COPY: Record<ApplicationStatus, StatusCopy> = {
  email_pending: {
    title: "تأكيد البريد الإلكتروني",
    description:
      "يرجى التحقق من بريدك الإلكتروني والنقر على رابط التأكيد.",
    iconName: "Mail",
    actionLabel: "إعادة الإرسال",
    actionHref: null,
  },
  under_review: {
    title: "قيد المراجعة",
    description:
      "طلبك قيد المراجعة حاليًا. سنُخطرك فور الانتهاء.",
    iconName: "Clock",
    actionLabel: null,
    actionHref: null,
  },
  changes_requested: {
    title: "مطلوب تعديلات",
    description:
      "طلب المراجع إجراء بعض التعديلات على طلبك. يرجى الاطلاع على الملاحظات.",
    iconName: "AlertTriangle",
    actionLabel: "عرض الملاحظات",
    actionHref: null,
  },
  approved: {
    title: "تمت الموافقة على الطلب",
    description:
      "تهانينا! تمت الموافقة على طلبك. يمكنك الآن الدخول إلى لوحة التحكم.",
    iconName: "CheckCircle",
    actionLabel: "الانتقال إلى البوابة",
    actionHref: "/saas/portal",
  },
  rejected: {
    title: "تم رفض الطلب",
    description:
      "للأسف، لم يتم قبول طلبك. يمكنك التواصل معنا لمزيد من التفاصيل.",
    iconName: "XCircle",
    actionLabel: null,
    actionHref: null,
  },
};
