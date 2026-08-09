import { AthkaLogo } from "@/components/brand/athka-logo";
import { ApplicationStatusCard } from "@/components/saas/application-status-card";

export const metadata = {
  title: "حالة الطلب | Athkachatbots",
};

export default function ApplicationStatusPage() {
  return (
    <main className="app-status-page">
      <div
        className="app-status-page__glow app-status-page__glow--one"
        aria-hidden="true"
      />
      <div
        className="app-status-page__glow app-status-page__glow--two"
        aria-hidden="true"
      />

      <div className="app-status-page__inner">
        <div className="app-status-page__logo">
          <AthkaLogo />
        </div>

        <ApplicationStatusCard />
      </div>
    </main>
  );
}
