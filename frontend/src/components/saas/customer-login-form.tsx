"use client";

import {
  ArrowLeft,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  Mail,
} from "lucide-react";
import {
  type FormEvent,
  useState,
} from "react";

type ErrorResponse = {
  detail?: unknown;
};

type LoginResponse = {
  application_status?: string;
};

const copy = {
  invalidCredentials:
    "البريد الإلكتروني أو كلمة المرور غير صحيحة",
  tooManyAttempts:
    "تم تجاوز عدد المحاولات. حاول مجددًا بعد قليل.",
  unavailable:
    "خدمة المصادقة غير متاحة حالياً.",
  genericError:
    "تعذر تسجيل الدخول. حاول مرة أخرى.",
  required:
    "أدخل البريد الإلكتروني وكلمة المرور.",
  connectionError:
    "تعذر الاتصال بالخادم. تحقق من اتصالك وحاول مجددًا.",
  email:
    "البريد الإلكتروني",
  emailPlaceholder:
    "أدخل بريدك الإلكتروني",
  password:
    "كلمة المرور",
  passwordPlaceholder:
    "أدخل كلمة المرور",
  hidePassword:
    "إخفاء كلمة المرور",
  showPassword:
    "إظهار كلمة المرور",
  signingIn:
    "جاري تسجيل الدخول",
  submit:
    "دخول إلى المنصة",
} as const;

function resolveErrorMessage(
  status: number,
  payload: ErrorResponse | null,
): string {
  if (status === 401) {
    return copy.invalidCredentials;
  }

  if (status === 429) {
    return copy.tooManyAttempts;
  }

  if (status === 502) {
    return copy.unavailable;
  }

  if (
    typeof payload?.detail === "string" &&
    payload.detail.trim()
  ) {
    return payload.detail;
  }

  return copy.genericError;
}

export function CustomerLoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] =
    useState(false);
  const [isSubmitting, setIsSubmitting] =
    useState(false);
  const [errorMessage, setErrorMessage] =
    useState<string | null>(null);

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const normalizedEmail = email.trim();

    if (!normalizedEmail || !password) {
      setErrorMessage(copy.required);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await fetch(
        "/api/tenant-auth/login",
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            email: normalizedEmail,
            password,
          }),
        },
      );

      const payload = (
        await response
          .json()
          .catch(() => null)
      ) as (LoginResponse & ErrorResponse) | null;

      if (!response.ok) {
        setErrorMessage(
          resolveErrorMessage(
            response.status,
            payload,
          ),
        );
        return;
      }

      if (payload?.application_status === "approved") {
        window.location.assign("/app/overview");
      } else {
        window.location.assign("/saas/application-status");
      }
    } catch {
      setErrorMessage(copy.connectionError);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form
      className="login-form"
      onSubmit={handleSubmit}
      noValidate
    >
      <div className="login-form__field">
        <label htmlFor="email">
          {copy.email}
        </label>

        <div className="login-form__control">
          <Mail aria-hidden="true" />

          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            autoCapitalize="none"
            spellCheck={false}
            placeholder={copy.emailPlaceholder}
            value={email}
            disabled={isSubmitting}
            onChange={(event) => {
              setEmail(event.target.value);
            }}
          />
        </div>
      </div>

      <div className="login-form__field">
        <label htmlFor="customer-password">
          {copy.password}
        </label>

        <div className="login-form__control">
          <LockKeyhole aria-hidden="true" />

          <input
            id="customer-password"
            name="password"
            type={
              showPassword
                ? "text"
                : "password"
            }
            autoComplete="current-password"
            placeholder={copy.passwordPlaceholder}
            value={password}
            disabled={isSubmitting}
            onChange={(event) => {
              setPassword(event.target.value);
            }}
          />

          <button
            className="login-form__visibility"
            type="button"
            aria-label={
              showPassword
                ? copy.hidePassword
                : copy.showPassword
            }
            aria-pressed={showPassword}
            disabled={isSubmitting}
            onClick={() => {
              setShowPassword(
                (current) => !current,
              );
            }}
          >
            {showPassword ? (
              <EyeOff aria-hidden="true" />
            ) : (
              <Eye aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      <div
        className="login-form__message"
        aria-live="polite"
      >
        {errorMessage && (
          <div
            className="login-form__error"
            role="alert"
          >
            {errorMessage}
          </div>
        )}
      </div>

      <button
        className="login-form__submit"
        type="submit"
        disabled={isSubmitting}
      >
        {isSubmitting ? (
          <>
            <LoaderCircle
              className="login-form__spinner"
              aria-hidden="true"
            />
            {copy.signingIn}
          </>
        ) : (
          <>
            {copy.submit}
            <ArrowLeft aria-hidden="true" />
          </>
        )}
      </button>
    </form>
  );
}
