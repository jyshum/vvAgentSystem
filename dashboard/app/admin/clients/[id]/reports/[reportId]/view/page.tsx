import { createAdminClient } from "@/lib/supabase/admin";
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
  const supabase = createAdminClient();

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
            "id, run_id, query_id, query, bucket, engine, model, brand_mentioned, brand_cited, citation_url, competitor_mentions, response_text, queried_at, run_number, mention_level, mention_level_label"
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
    <div
      className="no-print-wrapper"
      style={{
        position: "fixed",
        top: "78px",
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 40,
        display: "flex",
        flexDirection: "column",
        background: "#080809",
      }}
    >
      {/* Chrome bar */}
      <div
        className="no-print flex items-center justify-between px-6 flex-shrink-0"
        style={{
          height: "48px",
          borderBottom: "1px solid var(--hair)",
          background: "rgba(14,14,15,0.7)",
        }}
      >
        <div className="flex items-center gap-4">
          <Link
            href={`/admin/clients/${id}/reports`}
            className="font-mono text-[9px] tracking-[0.12em] uppercase transition-opacity hover:opacity-100 opacity-60"
            style={{ color: "var(--faint)" }}
          >
            ← Reports
          </Link>
          <span
            className="font-mono text-[9px] tracking-[0.12em] uppercase"
            style={{ color: "var(--faint)" }}
          >
            {typedClient.name}
          </span>
        </div>
        <div className="flex items-center gap-2">
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

      {/* Scrollable report area */}
      <div
        className="flex-1 overflow-y-auto"
        style={{ padding: "40px 24px 80px" }}
      >
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
    </div>
  );
}
