import Link from "next/link";
import {
  ArrowLeft,
  Bot,
  BookOpenCheck,
  Sparkles,
  UsersRound,
} from "lucide-react";

const copy = {
  eyebrow:
    "\u0645\u0631\u0643\u0632 \u0627\u0644\u062a\u062d\u0643\u0645",
  title:
    "\u0645\u0631\u062d\u0628\u064b\u0627 \u0641\u064a Athkachatbots",
  description:
    "\u0627\u0644\u0647\u064a\u0643\u0644 \u0627\u0644\u0623\u0633\u0627\u0633\u064a \u0644\u0644\u0648\u062d\u0629 \u0627\u0644\u0625\u062f\u0627\u0631\u0629 \u062c\u0627\u0647\u0632. \u0633\u0646\u0628\u0646\u064a \u0628\u0639\u062f\u0647 \u0646\u0638\u0631\u0629 \u0639\u0627\u0645\u0629 \u0645\u0631\u062a\u0628\u0637\u0629 \u0628\u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u0645\u0646\u0635\u0629 \u0627\u0644\u062d\u0642\u064a\u0642\u064a\u0629.",
  tenants:
    "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0639\u0645\u0644\u0627\u0621",
  tenantsDescription:
    "\u0625\u0646\u0634\u0627\u0621 \u0645\u0633\u0627\u062d\u0627\u062a \u0627\u0644\u0639\u0645\u0644\u0627\u0621 \u0648\u0625\u062f\u0627\u0631\u0629 \u062d\u0627\u0644\u0627\u062a\u0647\u0645.",
  agents:
    "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  agentsDescription:
    "\u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0648\u0631\u0628\u0637\u0647\u0645 \u0628\u0643\u0644 \u0639\u0645\u064a\u0644.",
  knowledge:
    "\u0645\u0635\u0627\u062f\u0631 \u0627\u0644\u0645\u0639\u0631\u0641\u0629",
  knowledgeDescription:
    "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0648\u0627\u0644\u0641\u0647\u0631\u0633\u0629 \u0648\u062d\u0627\u0644\u0627\u062a \u0627\u0644\u0627\u0633\u062a\u064a\u0639\u0627\u0628.",
  open:
    "\u0641\u062a\u062d \u0627\u0644\u0642\u0633\u0645",
  next:
    "\u0627\u0644\u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u062a\u0627\u0644\u064a\u0629",
  nextTitle:
    "\u0646\u0638\u0631\u0629 Dashboard \u0627\u0644\u0639\u0627\u0645\u0629",
  nextDescription:
    "\u0633\u0646\u0631\u0628\u0637 \u0628\u0637\u0627\u0642\u0627\u062a \u0627\u0644\u0625\u062d\u0635\u0627\u0621\u0627\u062a \u0648\u0627\u0644\u0646\u0634\u0627\u0637 \u0627\u0644\u0623\u062e\u064a\u0631 \u0648\u062d\u0627\u0644\u0629 \u0627\u0644\u0623\u0646\u0638\u0645\u0629 \u0628\u0648\u0627\u062c\u0647\u0627\u062a API \u0627\u0644\u062d\u0642\u064a\u0642\u064a\u0629.",
} as const;

const sections = [
  {
    title: copy.tenants,
    description: copy.tenantsDescription,
    href: "/dashboard/tenants",
    icon: UsersRound,
  },
  {
    title: copy.agents,
    description: copy.agentsDescription,
    href: "/dashboard/agents",
    icon: Bot,
  },
  {
    title: copy.knowledge,
    description: copy.knowledgeDescription,
    href: "/dashboard/knowledge-bases",
    icon: BookOpenCheck,
  },
];

export default function DashboardPage() {
  return (
    <main className="dashboard-overview">
      <section className="dashboard-welcome">
        <div>
          <span className="dashboard-welcome__eyebrow">
            <Sparkles aria-hidden="true" />
            {copy.eyebrow}
          </span>

          <h2>{copy.title}</h2>
          <p>{copy.description}</p>
        </div>

        <div
          className="dashboard-welcome__visual"
          aria-hidden="true"
        >
          <span />
          <span />
          <span />
          <span />
        </div>
      </section>

      <section
        className="dashboard-section-grid"
        aria-label={copy.eyebrow}
      >
        {sections.map((section) => {
          const Icon = section.icon;

          return (
            <Link
              key={section.href}
              className="dashboard-section-card"
              href={section.href}
            >
              <span className="dashboard-section-card__icon">
                <Icon aria-hidden="true" />
              </span>

              <div>
                <h3>{section.title}</h3>
                <p>{section.description}</p>
              </div>

              <span className="dashboard-section-card__action">
                {copy.open}
                <ArrowLeft aria-hidden="true" />
              </span>
            </Link>
          );
        })}
      </section>

      <section className="dashboard-next-step">
        <span>{copy.next}</span>
        <h2>{copy.nextTitle}</h2>
        <p>{copy.nextDescription}</p>
      </section>
    </main>
  );
}
