import { redirect } from "next/navigation";

export default async function ClientDetailRoot({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/admin/clients/${id}/overview`);
}
