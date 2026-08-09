"use client";

import { AlertCircle, CheckCircle, LoaderCircle } from "lucide-react";
import Link from "next/link";

type Props = {
  status: "verified" | "error" | "loading";
  message?: string;
};

export function VerifyEmailStatus({ status, message }: Props) {
  if (status === "loading") {
    return (
      <div className="verify-email-card__result">
        <div className="verify-email-card__icon">
          <LoaderCircle
            className="login-form__spinner"
            aria-hidden="true"
          />
        </div>

        <h2>جارٍ التحقق…</h2>

        <p>يرجى الانتظار بينما نتحقق من بريدك الإلكتروني.</p>
      </div>
    );
  }

  if (status === "verified") {
    return (
      <div className="verify-email-card__result">
        <div className="verify-email-card__icon is-success">
          <CheckCircle aria-hidden="true" />
        </div>

        <h2>تم التحقق من بريدك الإلكتروني بنجاح</h2>

        <p>
          {message ?? "تم التحقق من حسابك. يمكنك الآن متابعة طلبك."}
        </p>

        <Link
          href="/saas/application-status"
          className="verify-email-card__action"
        >
          عرض حالة الطلب
        </Link>
      </div>
    );
  }

  return (
    <div className="verify-email-card__result">
      <div className="verify-email-card__icon is-error">
        <AlertCircle aria-hidden="true" />
      </div>

      <h2>تعذر التحقق من البريد الإلكتروني</h2>

      <p>
        {message ??
          "الرابط غير صالح أو منتهي الصلاحية. حاول إعادة إرسال بريد التحقق."}
      </p>

      <Link
        href="/saas/signup"
        className="verify-email-card__action"
      >
        العودة للتسجيل
      </Link>
    </div>
  );
}
