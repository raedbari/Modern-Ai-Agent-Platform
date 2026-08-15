import { Check } from "lucide-react";
import Link from "next/link";

import type { Plan } from "@/lib/saas/plans";

type Props = {
  plan: Plan;
};

export function PricingCard({ plan }: Props) {
  const isFeatured = plan.id === "pro";
  const ctaText = plan.id === "starter" ? "ابدأ مجانًا" : "ابدأ الآن";

  return (
    <article
      className={
        isFeatured
          ? "pricing-card pricing-card--featured"
          : "pricing-card"
      }
      aria-label={plan.nameAr}
    >
      {isFeatured && (
        <span className="pricing-card__badge">الأكثر شيوعًا</span>
      )}

      <h3 className="pricing-card__name">{plan.nameAr}</h3>

      <p className="pricing-card__price">{plan.priceAr}</p>

      <ul className="pricing-card__features" aria-label="مميزات الخطة">
        {plan.features.map((feature) => (
          <li key={feature} className="pricing-card__feature">
            <Check aria-hidden={true} />
            <span>{feature}</span>
          </li>
        ))}
      </ul>

      <Link
        className="pricing-card__cta"
        href={`/saas/signup?plan=${plan.id}`}
      >
        {ctaText}
      </Link>
    </article>
  );
}
