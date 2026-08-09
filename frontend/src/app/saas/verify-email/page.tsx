import { Mail } from "lucide-react";

import { AthkaLogo } from "@/components/brand/athka-logo";
import { VerifyEmailStatus } from "@/components/saas/verify-email-status";
import {
  SaasApiError,
  SaasApiUnavailableError,
  verifyEmail,
} from "@/lib/server/saas-api";

type Props = {
  searchParams: Promise<{ token?: string }>;
};

export default async function VerifyEmailPage({
  searchParams,
}: Props) {
  const params = await searchParams;
  const token = params.token;

  if (token) {
    let status: "verified" | "error" = "error";
    let message: string | undefined;

    try {
      await verifyEmail({ token });
      status = "verified";
    } catch (error) {
      if (error instanceof SaasApiError) {
        if (typeof error.detail === "string" && error.detail.trim()) {
          message = error.detail;
        } else {
          message = "الرابط غير صالح أو منتهي الصلاحية. حاول مرة أخرى.";
        }
      } else if (error instanceof SaasApiUnavailableError) {
        message = "خدمة التحقق غير متاحة حاليًا. حاول لاحقًا.";
      } else {
        message = "تعذر الاتصال بالخادم. حاول مرة أخرى.";
      }
    }

    return (
      <main className="verify-email-page">
        <div className="verify-email-card">
          <div className="verify-email-card__logo">
            <AthkaLogo />
          </div>

          <VerifyEmailStatus status={status} message={message} />
        </div>
      </main>
    );
  }

  return (
    <main className="verify-email-page">
      <div className="verify-email-card">
        <div className="verify-email-card__logo">
          <AthkaLogo />
        </div>

        <div className="verify-email-card__icon">
          <Mail aria-hidden="true" />
        </div>

        <h2>تحقق من بريدك الإلكتروني</h2>

        <p>
          أرسلنا رابط التحقق إلى بريدك الإلكتروني. انقر على الرابط للتحقق
          من حسابك والمتابعة إلى خطوة مراجعة الطلب.
        </p>
      </div>
    </main>
  );
}
