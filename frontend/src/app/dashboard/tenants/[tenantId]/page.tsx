import {
  TenantDetailsView,
} from "@/components/tenants/tenant-details-view";

type Props = {
  params: Promise<{
    tenantId: string;
  }>;
};

export const metadata = {
  title:
    "\u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u0639\u0645\u064a\u0644",
};

export default async function TenantDetailsPage({
  params,
}: Props) {
  const {
    tenantId,
  } = await params;

  return (
    <TenantDetailsView
      tenantId={tenantId}
    />
  );
}
