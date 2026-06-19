import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";
import { ReportEditor } from "@/components/admin/ReportEditor";
import type { Report, TrackerRun, TrackerResultClient, Client } from "@/lib/types";

export default async function ReportEditorPage({
  params,
}: {
  params: Promise<{ id: string; reportId: string }>;
}) {
  const { id, reportId } = await params;
  const supabase = createAdminClient();

  const { data: report } = await supabase
    .from("reports")
    .select("*")
    .eq("id", reportId)
    .eq("client_id", id)
    .single();

  if (!report) notFound();
  const typedReport = report as Report;

  const [{ data: client }, runResult, resultsResult, { data: previousRuns }] = await Promise.all([
    supabase.from("clients").select("*").eq("id", id).single(),
    typedReport.run_id
      ? supabase.from("tracker_runs").select("*").eq("id", typedReport.run_id).single()
      : Promise.resolve({ data: null }),
    typedReport.run_id
      ? supabase
          .from("tracker_results")
          .select(
            "id, run_id, query, engine, model, brand_mentioned, brand_cited, citation_url, competitor_mentions, queried_at"
          )
          .eq("run_id", typedReport.run_id)
      : Promise.resolve({ data: [] }),
    supabase.from("tracker_runs").select("*").eq("client_id", id).order("ran_at", { ascending: false }).limit(5),
  ]);

  if (!client) notFound();

  return (
    <ReportEditor
      initialReport={typedReport}
      run={(runResult?.data as TrackerRun) ?? null}
      results={(resultsResult?.data as TrackerResultClient[]) ?? []}
      client={client as Client}
      previousRuns={(previousRuns as TrackerRun[]) ?? []}
    />
  );
}
