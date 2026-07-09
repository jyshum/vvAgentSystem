import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";
import { ConfigForm } from "@/components/admin/ConfigForm";
import { QueryBucketManager } from "@/components/admin/QueryBucketManager";
import type { Client, Query } from "@/lib/types";

export default async function ConfigPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = createAdminClient();

  const [{ data: client }, { data: queries }] = await Promise.all([
    supabase.from("clients").select("*").eq("id", id).single(),
    supabase
      .from("queries")
      .select("*")
      .eq("client_id", id)
      .order("created_at", { ascending: true }),
  ]);

  if (!client) notFound();

  return (
    <>
      <ConfigForm client={client as Client} />
      <QueryBucketManager clientId={id} initialQueries={(queries as Query[]) || []} />
    </>
  );
}
