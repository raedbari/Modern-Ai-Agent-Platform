import { Clock, UsersRound } from "lucide-react";

export const metadata = {
  title: "فريق العمل | بوابة العميل",
};

export default function TeamPage() {
  return (
    <div className="coming-soon-card">
      <div className="coming-soon-card__icon">
        <UsersRound aria-hidden="true" />
      </div>
      <h2>إدارة فريق العمل</h2>
      <p>
        ستتمكن قريباً من دعوة أعضاء فريقك وتحديد الأدوار والصلاحيات لكل عضو.
      </p>
      <div className="coming-soon-card__badge">
        <Clock aria-hidden="true" />
        <span>قريباً في المرحلة القادمة</span>
      </div>
    </div>
  );
}
