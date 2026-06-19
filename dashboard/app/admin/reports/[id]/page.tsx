import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";
import { ReportEditor } from "@/components/admin/ReportEditor";
import type {
  Report,
  TrackerRun,
  TrackerResultClient,
  Client,
} from "@/lib/types";

export default async function AdminReportEditorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = createAdminClient();

  const { data: report } = await supabase
    .from("reports")
    .select("*")
    .eq("id", id)
    .single();

  if (!report) notFound();

  const { data: client } = await supabase
    .from("clients")
    .select("*")
    .eq("id", report.client_id)
    .single();

  if (!client) notFound();

  let run: TrackerRun | null = null;
  let results: TrackerResultClient[] = [];
  let previousRuns: TrackerRun[] = [];

  if (report.run_id) {
    const { data: runData } = await supabase
      .from("tracker_runs")
      .select("*")
      .eq("id", report.run_id)
      .single();

    run = runData as TrackerRun | null;

    const { data: resultsData } = await supabase
      .from("tracker_results_client")
      .select("*")
      .eq("run_id", report.run_id);

    results = (resultsData as TrackerResultClient[]) || [];

    if (run) {
      const { data: prevRuns } = await supabase
        .from("tracker_runs")
        .select("*")
        .eq("client_id", report.client_id)
        .lt("ran_at", run.ran_at)
        .order("ran_at", { ascending: false })
        .limit(7);

      previousRuns = ((prevRuns as TrackerRun[]) || []).reverse();
    }
  }

  return (
    <ReportEditor
      initialReport={report as Report}
      run={run}
      results={results}
      client={client as Client}
      previousRuns={previousRuns}
    />
  );
}
