import type {
  PropsWithChildren,
} from "react";

import {
  DashboardShell,
} from "@/components/dashboard/dashboard-shell";

export default function DashboardLayout({
  children,
}: PropsWithChildren) {
  return (
    <DashboardShell>
      {children}
    </DashboardShell>
  );
}
