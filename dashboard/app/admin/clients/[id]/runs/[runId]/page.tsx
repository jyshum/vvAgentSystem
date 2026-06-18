import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import { RunDetail } from "@/components/admin/RunDetail";
import type { TrackerRun, TrackerResult, Client } from "@/lib/types";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string; runId: string }>;
}) {
  const { id, runId } = await params;
  const supabase = await createClient();

  const [{ data: run }, { data: results }, { data: client }] = await Promise.all([
    supabase.from("tracker_runs").select("*").eq("id", runId).eq("client_id", id).single(),
    supabase.from("tracker_results").select("*").eq("run_id", runId).order("queried_at"),
    supabase.from("clients").select("*").eq("id", id).single(),
  ]);

  if (!run || !client) notFound();

  return (
    <RunDetail
      run={run as TrackerRun}
      results={(results as TrackerResult[]) || []}
      client={client as Client}
      clientId={id}
    />
  );
}
