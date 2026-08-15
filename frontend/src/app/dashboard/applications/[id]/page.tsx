import { ApplicationDetail } from "@/components/admin/application-detail";

type Props = {
  params: Promise<{ id: string }>;
};

export const metadata = {
  title: "تفاصيل طلب الاشتراك | لوحة التحكم",
};

export default async function ApplicationDetailPage({ params }: Props) {
  const { id } = await params;

  return <ApplicationDetail applicationId={id} />;
}
