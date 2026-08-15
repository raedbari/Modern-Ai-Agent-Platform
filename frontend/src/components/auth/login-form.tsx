"use client";

import {
  ArrowLeft,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  UserRound,
} from "lucide-react";
import {
  type FormEvent,
  useState,
} from "react";

type ErrorResponse = {
  detail?: unknown;
};

const copy = {
  invalidCredentials:
    "\u0627\u0633\u0645 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645 \u0623\u0648 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631 \u063a\u064a\u0631 \u0635\u062d\u064a\u062d\u0629.",
  tooManyAttempts:
    "\u062a\u0645 \u062a\u062c\u0627\u0648\u0632 \u0639\u062f\u062f \u0645\u062d\u0627\u0648\u0644\u0627\u062a \u0627\u0644\u062f\u062e\u0648\u0644. \u062d\u0627\u0648\u0644 \u0645\u062c\u062f\u062f\u064b\u0627 \u0628\u0639\u062f \u0642\u0644\u064a\u0644.",
  unavailable:
    "\u062e\u062f\u0645\u0629 \u0627\u0644\u0645\u0635\u0627\u062f\u0642\u0629 \u063a\u064a\u0631 \u0645\u062a\u0627\u062d\u0629 \u062d\u0627\u0644\u064a\u064b\u0627.",
  genericError:
    "\u062a\u0639\u0630\u0631 \u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644. \u062d\u0627\u0648\u0644 \u0645\u0631\u0629 \u0623\u062e\u0631\u0649.",
  required:
    "\u0623\u062f\u062e\u0644 \u0627\u0633\u0645 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645 \u0648\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631.",
  connectionError:
    "\u062a\u0639\u0630\u0631 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0628\u0627\u0644\u062e\u0627\u062f\u0645. \u062a\u062d\u0642\u0642 \u0645\u0646 \u0627\u062a\u0635\u0627\u0644\u0643 \u0648\u062d\u0627\u0648\u0644 \u0645\u062c\u062f\u062f\u064b\u0627.",
  username:
    "\u0627\u0633\u0645 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645",
  usernamePlaceholder:
    "\u0623\u062f\u062e\u0644 \u0627\u0633\u0645 \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645",
  password:
    "\u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631",
  adminAccount:
    "\u062d\u0633\u0627\u0628 \u0627\u0644\u0645\u0633\u0624\u0648\u0644",
  passwordPlaceholder:
    "\u0623\u062f\u062e\u0644 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631",
  hidePassword:
    "\u0625\u062e\u0641\u0627\u0621 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631",
  showPassword:
    "\u0625\u0638\u0647\u0627\u0631 \u0643\u0644\u0645\u0629 \u0627\u0644\u0645\u0631\u0648\u0631",
  signingIn:
    "\u062c\u0627\u0631\u064a \u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u062f\u062e\u0648\u0644",
  submit:
    "\u062f\u062e\u0648\u0644 \u0625\u0644\u0649 \u0627\u0644\u0645\u0646\u0635\u0629",
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

export function LoginForm() {
  const [username, setUsername] = useState("");
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

    const normalizedUsername = username.trim();

    if (!normalizedUsername || !password) {
      setErrorMessage(copy.required);
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await fetch(
        "/api/auth/login",
        {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            username: normalizedUsername,
            password,
          }),
        },
      );

      const payload = (
        await response
          .json()
          .catch(() => null)
      ) as ErrorResponse | null;

      if (!response.ok) {
        setErrorMessage(
          resolveErrorMessage(
            response.status,
            payload,
          ),
        );
        return;
      }

      window.location.assign("/dashboard");
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
        <label htmlFor="username">
          {copy.username}
        </label>

        <div className="login-form__control">
          <UserRound aria-hidden="true" />

          <input
            id="username"
            name="username"
            type="text"
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            placeholder={copy.usernamePlaceholder}
            value={username}
            disabled={isSubmitting}
            onChange={(event) => {
              setUsername(event.target.value);
            }}
          />
        </div>
      </div>

      <div className="login-form__field">
        <div className="login-form__label-row">
          <label htmlFor="password">
            {copy.password}
          </label>

          <span>{copy.adminAccount}</span>
        </div>

        <div className="login-form__control">
          <LockKeyhole aria-hidden="true" />

          <input
            id="password"
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
