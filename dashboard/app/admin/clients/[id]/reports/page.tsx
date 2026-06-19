import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import { weekRangeLabel, formatRate, scoreColor } from "@/lib/utils";
import type { Report, TrackerRun } from "@/lib/types";

export default async function ReportsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

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
      <div className="flex items-center justify-end mb-8">
        <Link
          href={`/api/admin/create-report?clientId=${id}`}
          className="font-mono text-[9px] tracking-[0.14em] uppercase py-3 px-5 transition-all duration-200 hover:bg-[var(--white)] hover:text-[var(--ink)]"
          style={{ color: "var(--faint)", border: "1px solid var(--hair)", background: "transparent" }}
        >
          + NEW BLANK REPORT
        </Link>
      </div>

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

          {allReports.map((report) => {
            const run = report.run_id ? runsById[report.run_id] : null;
            return (
              <div
                key={report.id}
                className="grid items-center py-[17px] border-b transition-all duration-200 group hover:pl-2.5 cursor-pointer"
                style={{
                  gridTemplateColumns: "1.5fr 1fr 1fr 1fr 120px",
                  gap: "16px",
                  borderColor: "var(--hair)",
                }}
                onClick={() => { window.location.href = `/admin/clients/${id}/reports/${report.id}`; }}
              >
                {/* Week */}
                <div>
                  <div className="font-serif text-[16px]" style={{ color: "var(--white)" }}>
                    {weekRangeLabel(report.week_start) || "Untitled report"}
                  </div>
                  <div className="font-mono text-[8px] mt-0.5" style={{ color: "var(--faint)" }}>
                    {report.status === "published" ? "● Published" : "Draft"}
                  </div>
                </div>

                {/* Mention rate */}
                <div>
                  {run ? (
                    <div className="font-display font-light text-[22px] leading-none"
                      style={{ color: scoreColor(run.aggregate_mention_rate) }}>
                      {formatRate(run.aggregate_mention_rate)}
                    </div>
                  ) : (
                    <span className="font-mono text-[11px]" style={{ color: "var(--faint)" }}>—</span>
                  )}
                </div>

                {/* Citation rate */}
                <div>
                  {run ? (
                    <div className="font-display font-light text-[22px] leading-none"
                      style={{ color: scoreColor(run.aggregate_citation_rate) }}>
                      {formatRate(run.aggregate_citation_rate)}
                    </div>
                  ) : (
                    <span className="font-mono text-[11px]" style={{ color: "var(--faint)" }}>—</span>
                  )}
                </div>

                {/* Status */}
                <div className="font-mono text-[9px]" style={{ color: "var(--mute)" }}>
                  {new Date(report.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  {report.run_id ? " · from run" : " · blank"}
                </div>

                {/* Actions */}
                <div className="flex gap-1.5" onClick={(e) => e.stopPropagation()}>
                  <Link
                    href={`/admin/clients/${id}/reports/${report.id}`}
                    className="font-mono text-[8px] tracking-[0.08em] py-1.5 px-2.5 transition-all duration-200 hover:text-white hover:border-[var(--ghost)]"
                    style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
                  >
                    EDIT
                  </Link>
                  <Link
                    href={`/admin/clients/${id}/reports/${report.id}/view`}
                    className="font-mono text-[8px] tracking-[0.08em] py-1.5 px-2.5 transition-all duration-200 hover:text-white hover:border-[var(--ghost)]"
                    style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
                  >
                    VIEW ↗
                  </Link>
                </div>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
