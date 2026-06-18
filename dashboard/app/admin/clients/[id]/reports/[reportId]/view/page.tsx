import { createClient } from "@/lib/supabase/server";
import { notFound } from "next/navigation";
import Link from "next/link";
import { ReportView } from "@/components/report/ReportView";
import { PrintButton } from "@/components/ui/PrintButton";
import type { Report, TrackerRun, TrackerResultClient, Client } from "@/lib/types";

export default async function ReportViewPage({
  params,
}: {
  params: Promise<{ id: string; reportId: string }>;
}) {
  const { id, reportId } = await params;
  const supabase = await createClient();

  const [{ data: report }, { data: client }] = await Promise.all([
    supabase.from("reports").select("*").eq("id", reportId).eq("client_id", id).single(),
    supabase.from("clients").select("*").eq("id", id).single(),
  ]);

  if (!report || !client) notFound();
  const typedReport = report as Report;
  const typedClient = client as Client;

  const [runResult, resultsResult, prevRunsResult] = await Promise.all([
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
    supabase
      .from("tracker_runs")
      .select("*")
      .eq("client_id", id)
      .order("ran_at", { ascending: false })
      .limit(5),
  ]);

  return (
    <div style={{ background: "var(--ink)", minHeight: "60vh" }}>
      {/* Top bar */}
      <div
        className="no-print flex items-center justify-between py-3 px-4 mb-8 border-b"
        style={{ borderColor: "var(--hair)" }}
      >
        <Link
          href={`/admin/clients/${id}/reports`}
          className="font-mono text-[9px] tracking-[0.12em] uppercase transition-opacity hover:opacity-100 opacity-60"
          style={{ color: "var(--faint)" }}
        >
          ← Reports
        </Link>
        <div className="flex gap-2">
          <Link
            href={`/admin/clients/${id}/reports/${reportId}`}
            className="font-mono text-[9px] tracking-[0.1em] uppercase py-1.5 px-4 transition-colors hover:text-white"
            style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
          >
            EDIT
          </Link>
          <PrintButton />
        </div>
      </div>

      {/* Report content */}
      <ReportView
        report={typedReport}
        run={(runResult?.data as TrackerRun) ?? null}
        results={(resultsResult?.data as TrackerResultClient[]) ?? []}
        clientName={typedClient.name}
        brandName={typedClient.brand_name}
        domain={typedClient.website_domain}
        previousRuns={(prevRunsResult?.data as TrackerRun[]) ?? []}
      />
    </div>
  );
}
