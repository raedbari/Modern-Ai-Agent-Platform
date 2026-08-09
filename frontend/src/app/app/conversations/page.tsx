import { Clock, MessageSquareText } from "lucide-react";

export const metadata = {
  title: "المحادثات | بوابة العميل",
};

export default function ConversationsPage() {
  return (
    <div className="coming-soon-card">
      <div className="coming-soon-card__icon">
        <MessageSquareText aria-hidden="true" />
      </div>
      <h2>سجل ومتابعة المحادثات</h2>
      <p>
        ستتمكن قريباً من استعراض محادثات العملاء الحية وتحليلات الأداء والتحكم المباشر.
      </p>
      <div className="coming-soon-card__badge">
        <Clock aria-hidden="true" />
        <span>قريباً في المرحلة القادمة</span>
      </div>
    </div>
  );
}
