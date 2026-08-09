import { Clock, User } from "lucide-react";

export const metadata = {
  title: "إعدادات الحساب | بوابة العميل",
};

export default function AccountPage() {
  return (
    <div className="coming-soon-card">
      <div className="coming-soon-card__icon">
        <User aria-hidden="true" />
      </div>
      <h2>إعدادات الحساب والاشتراك</h2>
      <p>
        ستتمكن قريباً من تحديث بيانات المنشأة، إدارة الخطة واشتراك الفوترة، وتحديث كلمات المرور.
      </p>
      <div className="coming-soon-card__badge">
        <Clock aria-hidden="true" />
        <span>قريباً في المرحلة القادمة</span>
      </div>
    </div>
  );
}
