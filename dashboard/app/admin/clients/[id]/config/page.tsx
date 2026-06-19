import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";
import { ConfigForm } from "@/components/admin/ConfigForm";
import type { Client } from "@/lib/types";

export default async function ConfigPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = createAdminClient();

  const { data: client } = await supabase
    .from("clients")
    .select("*")
    .eq("id", id)
    .single();

  if (!client) notFound();

  return <ConfigForm client={client as Client} />;
}
