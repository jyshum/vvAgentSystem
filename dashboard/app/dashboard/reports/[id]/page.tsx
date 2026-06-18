import { createClient } from "@/lib/supabase/server";
import { redirect, notFound } from "next/navigation";
import { ReportView } from "@/components/report/ReportView";
import { PrintButton } from "@/components/ui/PrintButton";
import type { TrackerRun, TrackerResultClient } from "@/lib/types";

export default async function ClientReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

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
    <>
      <div className="no-print mb-6 flex justify-end">
        <PrintButton />
      </div>

      <ReportView
        report={report}
        run={run}
        results={results}
        clientName={client.name}
        brandName={client.brand_name}
        domain={client.website_domain}
        previousRuns={previousRuns}
      />
    </>
  );
}
