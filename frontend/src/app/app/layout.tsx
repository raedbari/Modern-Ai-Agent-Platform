import type { PropsWithChildren } from "react";
import { TenantShell } from "@/components/app/tenant-shell";

export const metadata = {
  title: "بوابة العميل | Athkachatbots",
};

export default function TenantLayout({ children }: PropsWithChildren) {
  return <TenantShell>{children}</TenantShell>;
}
