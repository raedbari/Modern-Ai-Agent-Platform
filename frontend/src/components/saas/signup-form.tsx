"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowLeft,
  Building2,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  Mail,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

const signupSchema = z.object({
  name: z.string().min(1, "الاسم مطلوب"),
  email: z
    .string()
    .min(1, "البريد الإلكتروني مطلوب")
    .email("صيغة البريد الإلكتروني غير صحيحة"),
  company_name: z.string().min(1, "اسم الشركة مطلوب"),
  password: z
    .string()
    .min(12, "كلمة المرور يجب أن تكون 8 أحرف على الأقل"),
  legal_accepted: z.literal(true, {
    errorMap: () => ({
      message: "يجب الموافقة على الشروط والأحكام للمتابعة",
    }),
  }),
});

type SignupFormValues = z.infer<typeof signupSchema>;

type ErrorResponse = {
  detail?: unknown;
};

type Props = {
  defaultPlan?: string;
};

function resolveServerError(
  status: number,
  payload: ErrorResponse | null,
): string {
  if (status === 409) {
    return "هذا البريد الإلكتروني مسجل بالفعل. يرجى تسجيل الدخول.";
  }

  if (status === 429) {
    return "تم تجاوز عدد المحاولات. حاول مجددًا بعد قليل.";
  }

  if (status === 502) {
    return "خدمة التسجيل غير متاحة حاليًا. حاول لاحقًا.";
  }

  if (
    typeof payload?.detail === "string" &&
    payload.detail.trim()
  ) {
    return payload.detail;
  }

  return "تعذر إتمام التسجيل. حاول مرة أخرى.";
}

export function SignupForm({ defaultPlan }: Props) {
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
  });

  async function onSubmit(values: SignupFormValues) {
    setServerError(null);

    try {
      const response = await fetch("/api/saas/signup", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          name: values.name,
          email: values.email,
          company_name: values.company_name,
          password: values.password,
          plan: defaultPlan ?? "starter",
          legal_accepted: values.legal_accepted,
        }),
      });

      const payload = (await response
        .json()
        .catch(() => null)) as ErrorResponse | null;

      if (!response.ok) {
        setServerError(
          resolveServerError(response.status, payload),
        );
        return;
      }

      window.location.assign("/saas/verify-email");
    } catch {
      setServerError(
        "تعذر الاتصال بالخادم. تحقق من اتصالك وحاول مجددًا.",
      );
    }
  }

  return (
    <form
      className="login-form"
      onSubmit={handleSubmit(onSubmit)}
      noValidate
    >
      {/* Name */}
      <div className="login-form__field">
        <label htmlFor="signup-name">الاسم</label>

        <div className="login-form__control">
          <UserRound aria-hidden="true" />

          <input
            id="signup-name"
            type="text"
            autoComplete="name"
            placeholder="أدخل اسمك الكامل"
            disabled={isSubmitting}
            {...register("name")}
          />
        </div>

        {errors.name && (
          <div className="login-form__error" role="alert">
            {errors.name.message}
          </div>
        )}
      </div>

      {/* Email */}
      <div className="login-form__field">
        <label htmlFor="signup-email">البريد الإلكتروني</label>

        <div className="login-form__control">
          <Mail aria-hidden="true" />

          <input
            id="signup-email"
            type="email"
            autoComplete="email"
            placeholder="أدخل بريدك الإلكتروني"
            disabled={isSubmitting}
            {...register("email")}
          />
        </div>

        {errors.email && (
          <div className="login-form__error" role="alert">
            {errors.email.message}
          </div>
        )}
      </div>

      {/* Company name */}
      <div className="login-form__field">
        <label htmlFor="signup-company">اسم الشركة</label>

        <div className="login-form__control">
          <Building2 aria-hidden="true" />

          <input
            id="signup-company"
            type="text"
            autoComplete="organization"
            placeholder="أدخل اسم شركتك"
            disabled={isSubmitting}
            {...register("company_name")}
          />
        </div>

        {errors.company_name && (
          <div className="login-form__error" role="alert">
            {errors.company_name.message}
          </div>
        )}
      </div>

      {/* Password */}
      <div className="login-form__field">
        <label htmlFor="signup-password">كلمة المرور</label>

        <div className="login-form__control">
          <LockKeyhole aria-hidden="true" />

          <input
            id="signup-password"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            placeholder="8 أحرف على الأقل"
            disabled={isSubmitting}
            {...register("password")}
          />

          <button
            className="login-form__visibility"
            type="button"
            aria-label={
              showPassword
                ? "إخفاء كلمة المرور"
                : "إظهار كلمة المرور"
            }
            aria-pressed={showPassword}
            disabled={isSubmitting}
            onClick={() => {
              setShowPassword((current) => !current);
            }}
          >
            {showPassword ? (
              <EyeOff aria-hidden="true" />
            ) : (
              <Eye aria-hidden="true" />
            )}
          </button>
        </div>

        {errors.password && (
          <div className="login-form__error" role="alert">
            {errors.password.message}
          </div>
        )}
      </div>

      {/* Legal accepted */}
      <div className="login-form__field">
        <label className="signup-form__checkbox">
          <input
            type="checkbox"
            disabled={isSubmitting}
            {...register("legal_accepted")}
          />
          <span>أوافق على الشروط والأحكام</span>
        </label>

        {errors.legal_accepted && (
          <div className="login-form__error" role="alert">
            {errors.legal_accepted.message}
          </div>
        )}
      </div>

      {/* Server error */}
      <div className="login-form__message" aria-live="polite">
        {serverError && (
          <div className="login-form__error" role="alert">
            {serverError}
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
            جارٍ التسجيل…
          </>
        ) : (
          <>
            إنشاء الحساب
            <ArrowLeft aria-hidden="true" />
          </>
        )}
      </button>
    </form>
  );
}
