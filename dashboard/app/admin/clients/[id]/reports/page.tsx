import { createAdminClient } from "@/lib/supabase/admin";
import Link from "next/link";
import { ReportRow } from "@/components/admin/ReportRow";
import type { Report, TrackerRun } from "@/lib/types";

export default async function ReportsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = createAdminClient();

  const { data: reports } = await supabase
    .from("reports")
    .select("*")
    .eq("client_id", id)
    .order("created_at", { ascending: false });

  const allReports = (reports as Report[]) || [];

  // Fetch runs for reports that have a run_id
  const runIds = allReports.map((r) => r.run_id).filter(Boolean) as string[];
  const runsById: Record<string, TrackerRun> = {};
  if (runIds.length > 0) {
    const { data: runs } = await supabase
      .from("tracker_runs")
      .select("id, aggregate_mention_rate, aggregate_citation_rate")
      .in("id", runIds);
    if (runs) {
      (runs as TrackerRun[]).forEach((run) => { runsById[run.id] = run; });
    }
  }

  return (
    <div>
      {allReports.length === 0 ? (
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No reports yet. Go to RUNS to create a report from a tracker run.
        </p>
      ) : (
        <>
          {/* Table header */}
          <div
            className="grid pb-2.5 border-b font-mono text-[8px] tracking-[0.14em] uppercase"
            style={{
              gridTemplateColumns: "1.5fr 1fr 1fr 1fr 120px",
              gap: "16px",
              borderColor: "var(--hair)",
              color: "var(--faint)",
            }}
          >
            <span>WEEK</span>
            <span>MENTION</span>
            <span>CITATION</span>
            <span>STATUS</span>
            <span>ACTIONS</span>
          </div>

          {allReports.map((report) => (
            <ReportRow
              key={report.id}
              report={report}
              clientId={id}
              run={report.run_id ? runsById[report.run_id] ?? null : null}
            />
          ))}
        </>
      )}
    </div>
  );
}
