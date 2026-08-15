import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { AthkaLogo } from "@/components/brand/athka-logo";
import { SignupForm } from "@/components/saas/signup-form";
import { PLANS } from "@/lib/saas/plans";

type Props = {
  searchParams: Promise<{ plan?: string }>;
};

export default async function SignupPage({ searchParams }: Props) {
  const params = await searchParams;
  const planId = params.plan;

  const found = planId
    ? PLANS.find((p) => p.id === planId)
    : undefined;

  const heading = found
    ? `سجّل في خطة ${found.nameAr}`
    : "إنشاء حساب جديد";

  return (
    <main className="signup-page">
      <div className="signup-card">
        <div className="signup-card__logo">
          <AthkaLogo />
        </div>

        <Link href="/saas" className="signup-card__back">
          <ArrowRight aria-hidden="true" />
          <span>العودة للأسعار</span>
        </Link>

        <div className="signup-card__heading">
          <h1>{heading}</h1>
        </div>

        <SignupForm defaultPlan={found?.id} />

        <p className="signup-card__login-link">
          لديك حساب؟{" "}
          <Link href="/saas/login">سجل دخول</Link>
        </p>
      </div>
    </main>
  );
}
