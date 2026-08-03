import {
  Activity,
  Database,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";

import { LoginForm } from "@/components/auth/login-form";
import { AthkaLogo } from "@/components/brand/athka-logo";

const copy = {
  systemsOperational:
    "\u062c\u0645\u064a\u0639 \u0627\u0644\u0623\u0646\u0638\u0645\u0629 \u062a\u0639\u0645\u0644",
  platformEyebrow:
    "\u0645\u0646\u0635\u0629 \u0648\u0643\u0644\u0627\u0621 \u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0629 \u0627\u0644\u0630\u0643\u064a\u0629",
  heroFirst:
    "\u0627\u0628\u0646\u0650 \u062a\u062c\u0631\u0628\u0629 \u0645\u062d\u0627\u062f\u062b\u0629",
  heroSecond:
    "\u0623\u0630\u0643\u0649 \u0644\u0639\u0645\u0644\u0627\u0626\u0643.",
  heroDescription:
    "\u0623\u0646\u0634\u0626 \u0648\u0643\u0644\u0627\u0621 \u0645\u062e\u0635\u0635\u064a\u0646\u060c \u0648\u0627\u0631\u0628\u0637 \u0645\u0635\u0627\u062f\u0631 \u0627\u0644\u0645\u0639\u0631\u0641\u0629\u060c \u0648\u0631\u0627\u0642\u0628 \u0627\u0644\u0623\u062f\u0627\u0621 \u0645\u0646 \u0644\u0648\u062d\u0629 \u062a\u062d\u0643\u0645 \u0648\u0627\u062d\u062f\u0629.",
  tenantIsolation:
    "\u0639\u0632\u0644 \u0643\u0627\u0645\u0644 \u0644\u0644\u0639\u0645\u0644\u0627\u0621",
  tenantIsolationDescription:
    "\u0628\u0646\u064a\u0629 \u0645\u062a\u0639\u062f\u062f\u0629 \u0627\u0644\u0639\u0645\u0644\u0627\u0621 \u0648\u0635\u0644\u0627\u062d\u064a\u0627\u062a \u062f\u0642\u064a\u0642\u0629",
  fastLaunch:
    "\u062a\u0634\u063a\u064a\u0644 \u0633\u0631\u064a\u0639",
  fastLaunchDescription:
    "\u0625\u0646\u0634\u0627\u0621 \u0648\u0646\u0634\u0631 \u0627\u0644\u0648\u0643\u064a\u0644 \u0628\u062e\u0637\u0648\u0627\u062a \u0648\u0627\u0636\u062d\u0629",
  productPanel:
    "\u0644\u0648\u062d\u0629 Athkachatbots",
  overview:
    "\u0646\u0638\u0631\u0629 \u0639\u0627\u0645\u0629",
  agentPerformance:
    "\u0623\u062f\u0627\u0621 \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
  live:
    "\u0645\u0628\u0627\u0634\u0631",
  conversations:
    "\u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0627\u062a",
  knowledgeSources:
    "\u0645\u0635\u0627\u062f\u0631 \u0627\u0644\u0645\u0639\u0631\u0641\u0629",
  synchronized:
    "\u0645\u062a\u0632\u0627\u0645\u0646\u0629",
  assistantMessage:
    "\u0643\u064a\u0641 \u064a\u0645\u0643\u0646\u0646\u064a \u0645\u0633\u0627\u0639\u062f\u062a\u0643 \u0627\u0644\u064a\u0648\u0645\u061f",
  userMessage:
    "\u0623\u0631\u064a\u062f \u0645\u0639\u0631\u0641\u0629 \u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u062e\u062f\u0645\u0629.",
  secureGateway:
    "\u0628\u0648\u0627\u0628\u0629 \u0627\u0644\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0622\u0645\u0646\u0629",
  welcome:
    "\u0645\u0631\u062d\u0628\u064b\u0627 \u0628\u0639\u0648\u062f\u062a\u0643",
  loginDescription:
    "\u0633\u062c\u0644 \u0627\u0644\u062f\u062e\u0648\u0644 \u0644\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0639\u0645\u0644\u0627\u0621 \u0648\u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0648\u0645\u0635\u0627\u062f\u0631 \u0627\u0644\u0645\u0639\u0631\u0641\u0629.",
  securityNotice:
    "\u062c\u0644\u0633\u0629 \u0622\u0645\u0646\u0629 \u0648\u0645\u062d\u0645\u064a\u0629 \u0628\u0627\u0633\u062a\u062e\u062f\u0627\u0645 Cookies \u0645\u0634\u0641\u0631\u0629 \u0648\u063a\u064a\u0631 \u0645\u062a\u0627\u062d\u0629 \u0644\u0644\u0645\u062a\u0635\u0641\u062d.",
  beta:
    "\u0627\u0644\u0625\u0635\u062f\u0627\u0631 \u0627\u0644\u062a\u062c\u0631\u064a\u0628\u064a",
} as const;

export default function LoginPage() {
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
                  <ShieldCheck aria-hidden="true" />
                </span>
                <strong>{copy.tenantIsolation}</strong>
                <small>
                  {copy.tenantIsolationDescription}
                </small>
              </div>

              <div>
                <span>
                  <Zap aria-hidden="true" />
                </span>
                <strong>{copy.fastLaunch}</strong>
                <small>
                  {copy.fastLaunchDescription}
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
            {copy.secureGateway}
          </div>

          <div className="auth-card__heading">
            <h2>{copy.welcome}</h2>
            <p>{copy.loginDescription}</p>
          </div>

          <LoginForm />

          <div className="auth-card__security">
            <ShieldCheck aria-hidden="true" />
            <span>{copy.securityNotice}</span>
          </div>

          <footer className="auth-card__footer">
            <span>? 2026 Athkachatbots</span>
            <span>{copy.beta}</span>
          </footer>
        </section>
      </section>
    </main>
  );
}
