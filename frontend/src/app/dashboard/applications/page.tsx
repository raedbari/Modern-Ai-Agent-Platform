import { ApplicationsList } from "@/components/admin/applications-list";

export const metadata = {
  title: "طلبات الاشتراك | لوحة التحكم",
};

export default function ApplicationsPage() {
  return (
    <div className="admin-page-container">
      <div className="admin-page-header">
        <div>
          <h1>طلبات اشتراك المنشآت</h1>
          <p>استعراض ومراجعة طلبات الانضمام لمنصة Athkachatbots</p>
        </div>
      </div>

      <ApplicationsList />
    </div>
  );
}
