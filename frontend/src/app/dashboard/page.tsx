import {
  ArrowLeft,
  Bot,
  LayoutDashboard,
  Sparkles,
} from "lucide-react";

import { AthkaLogo } from "@/components/brand/athka-logo";

export const metadata = {
  title:
    "\u0644\u0648\u062d\u0629 \u0627\u0644\u062a\u062d\u0643\u0645",
};

const copy = {
  adminWorkspace:
    "\u0645\u0633\u0627\u062d\u0629 \u0627\u0644\u0625\u062f\u0627\u0631\u0629",
  loginSuccess:
    "\u062a\u0645 \u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644 \u0628\u0646\u062c\u0627\u062d",
  nextInterface:
    "\u0633\u0646\u0628\u0646\u064a \u0627\u0644\u0647\u064a\u0643\u0644 \u0627\u0644\u0643\u0627\u0645\u0644 \u0644\u0644\u0648\u062d\u0629 \u0627\u0644\u062a\u062d\u0643\u0645 \u0641\u064a \u0627\u0644\u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u062a\u0627\u0644\u064a\u0629.",
  agents:
    "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  nextStep:
    "\u0627\u0644\u062e\u0637\u0648\u0629 \u0627\u0644\u062a\u0627\u0644\u064a\u0629",
} as const;

export default function DashboardPage() {
  return (
    <main className="dashboard-placeholder">
      <header className="dashboard-placeholder__header">
        <AthkaLogo />

        <span>
          <Sparkles aria-hidden="true" />
          {copy.adminWorkspace}
        </span>
      </header>

      <section className="dashboard-placeholder__card">
        <div className="dashboard-placeholder__icon">
          <LayoutDashboard aria-hidden="true" />
        </div>

        <small>Athkachatbots Dashboard</small>

        <h1>{copy.loginSuccess}</h1>

        <p>{copy.nextInterface}</p>

        <div className="dashboard-placeholder__items">
          <span>
            <Bot aria-hidden="true" />
            {copy.agents}
          </span>

          <span>
            <ArrowLeft aria-hidden="true" />
            {copy.nextStep}
          </span>
        </div>
      </section>
    </main>
  );
}
