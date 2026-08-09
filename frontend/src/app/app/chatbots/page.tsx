import { Bot, Clock } from "lucide-react";

export const metadata = {
  title: "الوكلاء الذكية | بوابة العميل",
};

export default function ChatbotsPage() {
  return (
    <div className="coming-soon-card">
      <div className="coming-soon-card__icon">
        <Bot aria-hidden="true" />
      </div>
      <h2>إدارة الوكلاء الذكية</h2>
      <p>
        ستتمكن قريباً من بناء وتخصيص وكلاء محادثة ذكية متخصصة لنشاطك التجاري.
      </p>
      <div className="coming-soon-card__badge">
        <Clock aria-hidden="true" />
        <span>قريباً في المرحلة القادمة</span>
      </div>
    </div>
  );
}
