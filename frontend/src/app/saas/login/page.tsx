import {
  Activity,
  Database,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import Link from "next/link";

import { AthkaLogo } from "@/components/brand/athka-logo";
import { CustomerLoginForm } from "@/components/saas/customer-login-form";

const copy = {
  systemsOperational:
    "جميع الأنظمة تعمل",
  platformEyebrow:
    "منصة وكلاء المحادثة الذكية",
  heroFirst:
    "وكيل ذكي لخدمة",
  heroSecond:
    "عملائك على مدار الساعة.",
  heroDescription:
    "استخدم Athkachatbots لبناء وكلاء محادثة ذكية تخدم عملاءك تلقائيًا، تجيب على استفساراتهم، وترفع مستوى تجربتهم.",
  instantSupport:
    "دعم فوري للعملاء",
  instantSupportDescription:
    "ردود آنية على أسئلة العملاء في أي وقت",
  easySetup:
    "إعداد سهل وسريع",
  easySetupDescription:
    "ابدأ في دقائق دون الحاجة لخبرة تقنية",
  productPanel:
    "لوحة Athkachatbots",
  overview:
    "نظرة عامة",
  agentPerformance:
    "أداء الوكلاء",
  live:
    "مباشر",
  conversations:
    "المحادثات",
  knowledgeSources:
    "مصادر المعرفة",
  synchronized:
    "متزامنة",
  assistantMessage:
    "كيف يمكنني مساعدتك اليوم؟",
  userMessage:
    "أريد معرفة تفاصيل الخدمة.",
  welcome:
    "مرحبًا بعودتك",
  loginDescription:
    "سجل الدخول للوصول إلى لوحة التحكم وإدارة وكلاء المحادثة.",
  securityNotice:
    "جلسة آمنة ومحمية باستخدام Cookies مشفرة وغير متاحة للمتصفح.",
  noAccount:
    "ليس لديك حساب؟",
  signUp:
    "سجل الآن",
  beta:
    "الإصدار التجريبي",
} as const;

export default function CustomerLoginPage() {
  return (
    <main className="auth-page">
      <div
        className="auth-page__glow auth-page__glow--one"
        aria-hidden="true"
      />
      <div
        className="auth-page__glow auth-page__glow--two"
        aria-hidden="true"
      />
      <div
        className="auth-page__grid"
        aria-hidden="true"
      />

      <section className="auth-layout">
        <aside className="auth-showcase">
          <div className="auth-showcase__header">
            <AthkaLogo />

            <div className="auth-showcase__status">
              <span />
              {copy.systemsOperational}
            </div>
          </div>

          <div className="auth-showcase__content">
            <div className="auth-showcase__eyebrow">
              <Sparkles aria-hidden="true" />
              {copy.platformEyebrow}
            </div>

            <h1>
              {copy.heroFirst}
              <span>{copy.heroSecond}</span>
            </h1>

            <p>{copy.heroDescription}</p>

            <div className="auth-benefits">
              <div>
                <span>
                  <MessageSquareText aria-hidden="true" />
                </span>
                <strong>{copy.instantSupport}</strong>
                <small>
                  {copy.instantSupportDescription}
                </small>
              </div>

              <div>
                <span>
                  <Zap aria-hidden="true" />
                </span>
                <strong>{copy.easySetup}</strong>
                <small>
                  {copy.easySetupDescription}
                </small>
              </div>
            </div>
          </div>

          <div className="product-preview">
            <div className="product-preview__topbar">
              <div>
                <span />
                <span />
                <span />
              </div>

              <small>{copy.productPanel}</small>
            </div>

            <div className="product-preview__body">
              <div className="product-preview__sidebar">
                <div className="preview-brand">
                  <MessageSquareText
                    aria-hidden="true"
                  />
                </div>

                <span className="is-active" />
                <span />
                <span />
                <span />
              </div>

              <div className="product-preview__workspace">
                <div className="preview-heading">
                  <div>
                    <small>{copy.overview}</small>
                    <strong>
                      {copy.agentPerformance}
                    </strong>
                  </div>

                  <div className="preview-chip">
                    {copy.live}
                  </div>
                </div>

                <div className="preview-metrics">
                  <div>
                    <Activity aria-hidden="true" />
                    <span>{copy.conversations}</span>
                    <strong>12,840</strong>
                    <small>+18.4%</small>
                  </div>

                  <div>
                    <Database aria-hidden="true" />
                    <span>
                      {copy.knowledgeSources}
                    </span>
                    <strong>128</strong>
                    <small>{copy.synchronized}</small>
                  </div>
                </div>

                <div className="preview-panel">
                  <div className="preview-chart">
                    <span style={{ height: "33%" }} />
                    <span style={{ height: "52%" }} />
                    <span style={{ height: "44%" }} />
                    <span style={{ height: "68%" }} />
                    <span style={{ height: "57%" }} />
                    <span style={{ height: "82%" }} />
                    <span style={{ height: "73%" }} />
                    <span style={{ height: "94%" }} />
                  </div>

                  <div className="preview-chat">
                    <div className="preview-chat__agent">
                      {copy.assistantMessage}
                    </div>
                    <div className="preview-chat__user">
                      {copy.userMessage}
                    </div>
                    <div className="preview-chat__typing">
                      <i />
                      <i />
                      <i />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>

        <section className="auth-card">
          <div className="auth-card__mobile-brand">
            <AthkaLogo />
          </div>

          <div className="auth-card__badge">
            <ShieldCheck aria-hidden="true" />
            بوابة العملاء الآمنة
          </div>

          <div className="auth-card__heading">
            <h2>{copy.welcome}</h2>
            <p>{copy.loginDescription}</p>
          </div>

          <CustomerLoginForm />

          <div className="auth-card__switch-link">
            <span>{copy.noAccount}</span>
            <Link href="/saas/signup">{copy.signUp}</Link>
          </div>

          <div className="auth-card__security">
            <ShieldCheck aria-hidden="true" />
            <span>{copy.securityNotice}</span>
          </div>

          <footer className="auth-card__footer">
            <span>© 2026 Athkachatbots</span>
            <span>{copy.beta}</span>
          </footer>
        </section>
      </section>
    </main>
  );
}
