import {
  Bot,
  BookOpenCheck,
  KeyRound,
  MessageSquareText,
  ScrollText,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  UsersRound,
} from "lucide-react";

const sections = {
  tenants: {
    title:
      "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0639\u0645\u0644\u0627\u0621",
    description:
      "\u0633\u0646\u0628\u0646\u064a \u0647\u0630\u0647 \u0627\u0644\u0648\u0627\u062c\u0647\u0629 \u0628\u0639\u062f \u0625\u0643\u0645\u0627\u0644 Dashboard.",
    icon: UsersRound,
  },
  agents: {
    title:
      "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
    description:
      "\u0633\u0646\u0628\u0646\u064a \u0647\u0630\u0647 \u0627\u0644\u0648\u0627\u062c\u0647\u0629 \u0628\u0639\u062f \u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u0639\u0645\u0644\u0627\u0621.",
    icon: Bot,
  },
  "knowledge-bases": {
    title:
      "\u0645\u0635\u0627\u062f\u0631 \u0627\u0644\u0645\u0639\u0631\u0641\u0629",
    description:
      "\u0633\u0646\u0631\u0628\u0637\u0647\u0627 \u0628\u0627\u0644\u0645\u0644\u0641\u0627\u062a \u0648\u0639\u0645\u0644\u064a\u0627\u062a \u0627\u0644\u0641\u0647\u0631\u0633\u0629.",
    icon: BookOpenCheck,
  },
  conversations: {
    title:
      "\u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0627\u062a",
    description:
      "\u0633\u0646\u0639\u0631\u0636 \u0645\u062d\u0627\u062f\u062b\u0627\u062a \u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0648\u0627\u0644\u0631\u0633\u0627\u0626\u0644 \u0628\u0634\u0643\u0644 \u0622\u0645\u0646.",
    icon: MessageSquareText,
  },
  "widget-settings": {
    title:
      "\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0648\u064a\u062f\u062c\u062a",
    description:
      "\u0633\u0646\u0628\u0646\u064a \u0645\u062d\u0631\u0631 \u0627\u0644\u0645\u0638\u0647\u0631 \u0648\u0627\u0644\u0645\u0639\u0627\u064a\u0646\u0629 \u0648\u0643\u0648\u062f \u0627\u0644\u062f\u0645\u062c.",
    icon: SlidersHorizontal,
  },
  "api-keys": {
    title:
      "\u0645\u0641\u0627\u062a\u064a\u062d API",
    description:
      "\u0633\u0646\u062f\u064a\u0631 \u0625\u0646\u0634\u0627\u0621 \u0627\u0644\u0645\u0641\u0627\u062a\u064a\u062d \u0648\u0625\u0644\u063a\u0627\u0621\u0647\u0627 \u0648\u062a\u062f\u0648\u064a\u0631\u0647\u0627.",
    icon: KeyRound,
  },
  "admin-users": {
    title:
      "\u0645\u0633\u0624\u0648\u0644\u0648 \u0627\u0644\u0645\u0646\u0635\u0629",
    description:
      "\u0633\u0646\u0628\u0646\u064a \u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u062d\u0633\u0627\u0628\u0627\u062a \u0648\u0627\u0644\u0623\u062f\u0648\u0627\u0631 \u0648\u0627\u0644\u0635\u0644\u0627\u062d\u064a\u0627\u062a.",
    icon: ShieldCheck,
  },
  "audit-logs": {
    title:
      "\u0633\u062c\u0644\u0627\u062a \u0627\u0644\u062a\u062f\u0642\u064a\u0642",
    description:
      "\u0633\u0646\u0639\u0631\u0636 \u0627\u0644\u0623\u062d\u062f\u0627\u062b \u0627\u0644\u0623\u0645\u0646\u064a\u0629 \u0648\u0627\u0644\u062a\u063a\u064a\u064a\u0631\u0627\u062a \u0627\u0644\u0625\u062f\u0627\u0631\u064a\u0629.",
    icon: ScrollText,
  },
  "system-settings": {
    title:
      "\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0646\u0638\u0627\u0645",
    description:
      "\u0633\u0646\u062c\u0645\u0639 \u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u062d\u0633\u0627\u0628 \u0648\u0627\u0644\u0623\u0645\u0627\u0646 \u0648\u062a\u063a\u064a\u064a\u0631 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631.",
    icon: Settings,
  },
} as const;

const fallback = {
  title:
    "\u0642\u0633\u0645 Athkachatbots",
  description:
    "\u0647\u0630\u0647 \u0627\u0644\u0648\u0627\u062c\u0647\u0629 \u0636\u0645\u0646 \u062e\u0637\u0629 \u0628\u0646\u0627\u0621 \u0627\u0644\u0645\u0646\u0635\u0629.",
  icon: Sparkles,
};

export default async function SectionPlaceholder({
  params,
}: {
  params: Promise<{
    section: string[];
  }>;
}) {
  const {
    section,
  } = await params;

  const current =
    sections[
      section[0] as keyof typeof sections
    ] ?? fallback;

  const Icon = current.icon;

  return (
    <main className="dashboard-placeholder-view">
      <div className="dashboard-placeholder-view__icon">
        <Icon aria-hidden="true" />
      </div>

      <span>Athkachatbots</span>
      <h2>{current.title}</h2>
      <p>{current.description}</p>
    </main>
  );
}
