import {
  Building2,
  CalendarDays,
  CheckCircle2,
  CreditCard,
  Mail,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import { getCurrentTenantProfile } from "@/lib/server/tenant-session";

export const metadata = {
  title: "الحساب والإعدادات | بوابة العميل",
};

function roleLabel(role: string | null): string {
  if (role === "tenant_admin") return "مسؤول الحساب";
  if (role === "tenant_member") return "عضو في مساحة العمل";
  return role || "مستخدم مساحة العمل";
}

function formatDate(value?: string): string {
  if (!value) return "غير متوفر";

  return new Intl.DateTimeFormat("ar", {
    dateStyle: "medium",
  }).format(new Date(value));
}

export default async function AccountPage() {
  const profile = await getCurrentTenantProfile();
  const companyName = profile.company_name || "مساحة عمل Athka";
  const initials = companyName.slice(0, 2).toUpperCase();

  return (
    <div className="customer-account" dir="rtl">
      <header className="customer-account__hero">
        <div>
          <span className="customer-account__eyebrow">إدارة الحساب</span>
          <h2>الحساب والإعدادات</h2>
          <p>راجع بيانات مساحة العمل وحالة اشتراكك من مكان واحد.</p>
        </div>
        <div className="customer-account__status">
          <CheckCircle2 aria-hidden="true" />
          <span>الحساب نشط</span>
        </div>
      </header>

      <section className="customer-account__profile-card" aria-labelledby="profile-title">
        <div className="customer-account__profile-heading">
          <span className="customer-account__avatar" aria-hidden="true">
            {initials}
          </span>
          <div>
            <span className="customer-account__label">مساحة العمل</span>
            <h3 id="profile-title">{companyName}</h3>
            <p>{profile.email}</p>
          </div>
          <ShieldCheck className="customer-account__verified" aria-label="حساب موثق" />
        </div>

        <div className="customer-account__details">
          <div className="customer-account__detail">
            <span className="customer-account__detail-icon"><Mail aria-hidden="true" /></span>
            <div><span>البريد الإلكتروني</span><strong>{profile.email}</strong></div>
          </div>
          <div className="customer-account__detail">
            <span className="customer-account__detail-icon"><UserRound aria-hidden="true" /></span>
            <div><span>نوع الحساب</span><strong>{roleLabel(profile.role)}</strong></div>
          </div>
          <div className="customer-account__detail">
            <span className="customer-account__detail-icon"><Building2 aria-hidden="true" /></span>
            <div><span>معرّف مساحة العمل</span><strong>{profile.tenant_id || "غير متوفر"}</strong></div>
          </div>
          <div className="customer-account__detail">
            <span className="customer-account__detail-icon"><CalendarDays aria-hidden="true" /></span>
            <div><span>تاريخ الانضمام</span><strong>{formatDate(profile.submitted_at)}</strong></div>
          </div>
        </div>
      </section>

      <section className="customer-account__plan-card" aria-labelledby="plan-title">
        <div className="customer-account__plan-icon"><CreditCard aria-hidden="true" /></div>
        <div>
          <span className="customer-account__label">الخطة والاشتراك</span>
          <h3 id="plan-title">الخطة التجريبية</h3>
          <p>يمكنك إدارة الفوترة والترقية إلى خطة مدفوعة في المرحلة القادمة.</p>
        </div>
        <span className="customer-account__coming-soon">قريبًا</span>
      </section>
    </div>
  );
}
