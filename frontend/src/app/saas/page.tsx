import Link from "next/link";

import { AthkaLogo } from "@/components/brand/athka-logo";
import { PricingCard } from "@/components/saas/pricing-card";
import { PLANS } from "@/lib/saas/plans";

export default function SaasLandingPage() {
  return (
    <main className="saas-landing" dir="rtl">
      {/* Navigation */}
      <nav className="saas-nav" aria-label="التنقل الرئيسي">
        <div className="saas-nav__inner">
          <AthkaLogo />
          <Link className="saas-nav__login" href="/saas/login">
            تسجيل الدخول
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="saas-hero" aria-labelledby="saas-hero-heading">
        <h1 id="saas-hero-heading" className="saas-hero__headline">
          اجعل خدمة عملائك أذكى مع{" "}
          <span className="saas-hero__brand">Athkachatbots</span>
        </h1>
        <p className="saas-hero__subtext">
          ابنِ وكلاء محادثة ذكية تخدم عملاءك تلقائيًا على مدار الساعة —
          دون الحاجة إلى خبرة تقنية. أجب على الاستفسارات، ورفّع مستوى
          تجربة عملائك من اليوم الأول.
        </p>
      </section>

      {/* Pricing plans */}
      <section
        className="saas-plans"
        aria-labelledby="saas-plans-heading"
      >
        <h2 id="saas-plans-heading" className="saas-plans__heading">
          اختر الخطة المناسبة
        </h2>
        <div className="saas-plans__grid">
          {PLANS.map((plan) => (
            <PricingCard key={plan.id} plan={plan} />
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="saas-footer">
        <span>© 2026 Athkachatbots. جميع الحقوق محفوظة.</span>
      </footer>
    </main>
  );
}
