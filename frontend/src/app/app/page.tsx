import { redirect } from "next/navigation";

export default function TenantAppRootPage() {
  redirect("/app/overview");
}
