"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  Brain,
  Check,
  Code2,
  Eye,
  MessageSquareText,
  Palette,
  Rocket,
  SlidersHorizontal,
} from "lucide-react";

import styles from "./chatbot-wizard.module.css";

const steps = [
  {
    id: 1,
    title: "?????????",
    description: "??? Chatbot ?????? ???",
    icon: Bot,
  },
  {
    id: 2,
    title: "???????",
    description: "????????? ?????? ???????",
    icon: Brain,
  },
  {
    id: 3,
    title: "??????",
    description: "????? ???? ??????????",
    icon: SlidersHorizontal,
  },
  {
    id: 4,
    title: "??????",
    description: "??????? ??????",
    icon: Palette,
  },
  {
    id: 5,
    title: "???????",
    description: "???? Chatbot ??? ????",
    icon: MessageSquareText,
  },
  {
    id: 6,
    title: "?????",
    description: "????? Chatbot",
    icon: Rocket,
  },
  {
    id: 7,
    title: "?????",
    description: "??? ?? ?????",
    icon: Code2,
  },
] as const;

export function ChatbotWizard() {
  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [purpose, setPurpose] = useState("");

  const current = steps[step - 1];

  function nextStep() {
    setStep((value) => Math.min(7, value + 1));
  }

  function previousStep() {
    setStep((value) => Math.max(1, value - 1));
  }

  return (
    <main className={styles.page} dir="rtl">
      <header className={styles.header}>
        <div>
          <Link
            href="/app/chatbots"
            className={styles.backLink}
          >
            <ArrowRight aria-hidden="true" />
            ?????? ??? Chatbots
          </Link>

          <h2>????? Chatbot ????</h2>

          <p>
            ????? ??????? ??? ???? ?????.
          </p>
        </div>

        <div className={styles.progressText}>
          ?????? {step} ?? {steps.length}
        </div>
      </header>

      <div className={styles.layout}>
        <aside className={styles.steps}>
          {steps.map((item) => {
            const Icon = item.icon;
            const active = item.id === step;
            const complete = item.id < step;

            return (
              <button
                key={item.id}
                type="button"
                className={[
                  styles.step,
                  active ? styles.active : "",
                  complete ? styles.complete : "",
                ].join(" ")}
                onClick={() => {
                  if (item.id <= step) {
                    setStep(item.id);
                  }
                }}
              >
                <span className={styles.stepIcon}>
                  {complete ? (
                    <Check aria-hidden="true" />
                  ) : (
                    <Icon aria-hidden="true" />
                  )}
                </span>

                <span>
                  <strong>{item.title}</strong>
                  <small>{item.description}</small>
                </span>
              </button>
            );
          })}
        </aside>

        <section className={styles.card}>
          <div className={styles.cardHeading}>
            <span>?????? {step}</span>
            <h3>{current.title}</h3>
            <p>{current.description}</p>
          </div>

          {step === 1 ? (
            <div className={styles.form}>
              <label>
                <span>??? Chatbot</span>

                <input
                  value={name}
                  onChange={(event) =>
                    setName(event.target.value)
                  }
                  placeholder="????: ????? ???? ???????"
                  maxLength={120}
                  autoFocus
                />

                <small>
                  ????? ???? ????? ?? ???? ???? ??????.
                </small>
              </label>

              <label>
                <span>?? ????? ?? Chatbot?</span>

                <textarea
                  value={purpose}
                  onChange={(event) =>
                    setPurpose(event.target.value)
                  }
                  placeholder={
                    "????: ??????? ?? ????? ??????? " +
                    "??? ????? ?????? ????????."
                  }
                  rows={5}
                  maxLength={1000}
                />
              </label>

              <div className={styles.notice}>
                <Eye aria-hidden="true" />
                <div>
                  <strong>???? ????? ???? ??????? ??????</strong>
                  <p>
                    ????? ????? ??? ???????? ???????? Chatbot
                    ??? ?????? ???????.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className={styles.placeholder}>
              <current.icon aria-hidden="true" />
              <h4>{current.title}</h4>
              <p>
                ???? ??? ??? ?????? ??????? ??????? ??
                ?????? ?? ???Milestone ??????.
              </p>
            </div>
          )}

          <footer className={styles.actions}>
            <button
              type="button"
              className={styles.secondary}
              disabled={step === 1}
              onClick={previousStep}
            >
              <ArrowRight aria-hidden="true" />
              ??????
            </button>

            {step < 7 ? (
              <button
                type="button"
                className={styles.primary}
                disabled={
                  step === 1 &&
                  name.trim().length < 2
                }
                onClick={nextStep}
              >
                ??????
                <ArrowLeft aria-hidden="true" />
              </button>
            ) : (
              <Link
                href="/app/chatbots"
                className={styles.primary}
              >
                ?????
                <Check aria-hidden="true" />
              </Link>
            )}
          </footer>
        </section>
      </div>
    </main>
  );
}
