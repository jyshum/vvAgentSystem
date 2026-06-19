import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import { TriggerRunButton } from "@/components/admin/TriggerRunButton";
import { scoreColor, formatRate } from "@/lib/utils";
import type { TrackerRun, Report, Client } from "@/lib/types";

export default async function RunsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const [{ data: clientData }, { data: runs }, { data: reports }] = await Promise.all([
    supabase.from("clients").select("name, target_queries").eq("id", id).single(),
    supabase
      .from("tracker_runs")
      .select("*")
      .eq("client_id", id)
      .order("ran_at", { ascending: false }),
    supabase
      .from("reports")
      .select("id, run_id")
      .eq("client_id", id),
  ]);

  const client = clientData as Pick<Client, "name" | "target_queries"> | null;
  const allRuns = (runs as TrackerRun[]) || [];
  const reportedRunIds = new Set(
    ((reports || []) as Pick<Report, "id" | "run_id">[])
      .map((r) => r.run_id)
      .filter(Boolean) as string[]
  );
  const expectedQueries = client?.target_queries?.length ?? 8;

  // Fetch result counts per run for QUERIES column
  const runResultCounts: Record<string, number> = {};
  if (allRuns.length > 0) {
    const { data: counts } = await supabase
      .from("tracker_results")
      .select("run_id")
      .in("run_id", allRuns.map((r) => r.id));
    if (counts) {
      counts.forEach((row: { run_id: string }) => {
        runResultCounts[row.run_id] = (runResultCounts[row.run_id] || 0) + 1;
      });
    }
  }

  return (
    <div>
      {/* Run box */}
      <div
        className="flex items-center justify-between mb-9 p-6"
        style={{ border: "1px solid var(--hair)" }}
      >
        <div>
          <div className="font-serif text-[17px] mb-1.5" style={{ color: "var(--white)" }}>
            Run AI Visibility Tracker
          </div>
          <div className="font-mono text-[9px] leading-relaxed tracking-[0.06em]" style={{ color: "var(--faint)" }}>
            Queries all 4 engines (ChatGPT · Perplexity · Claude · Gemini) against {client?.name ?? "this client"}&apos;s {expectedQueries} tracked queries.<br />
            Results are saved automatically when complete.
          </div>
        </div>
        <TriggerRunButton clientId={id} />
      </div>

      {allRuns.length === 0 ? (
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No runs yet. Click RUN NOW to start the first one.
        </p>
      ) : (
        <>
          {/* Table header */}
          <div
            className="grid pb-2.5 border-b font-mono text-[8px] tracking-[0.14em] uppercase"
            style={{
              gridTemplateColumns: "1.5fr 1fr 1fr 80px 1fr 110px",
              gap: "16px",
              borderColor: "var(--hair)",
              color: "var(--faint)",
            }}
          >
            <span>DATE</span>
            <span>MENTION</span>
            <span>CITATION</span>
            <span>QUERIES</span>
            <span>STATUS</span>
            <span>REPORT</span>
          </div>

          {allRuns.map((run) => {
            const resultCount = runResultCounts[run.id] ?? 0;
            const queryCount = resultCount > 0 ? Math.min(Math.round(resultCount / 4), expectedQueries) : 0;
            const hasData = run.aggregate_mention_rate != null;
            const isReported = reportedRunIds.has(run.id);

            return (
              <div
                key={run.id}
                className="grid items-center py-[17px] border-b group transition-all duration-200 cursor-pointer hover:pl-3"
                style={{
                  gridTemplateColumns: "1.5fr 1fr 1fr 80px 1fr 110px",
                  gap: "16px",
                  borderColor: "var(--hair)",
                }}
                onClick={() => { window.location.href = `/admin/clients/${id}/runs/${run.id}`; }}
              >
                {/* Date */}
                <div>
                  <div className="font-serif text-[15px]" style={{ color: "var(--white)" }}>
                    {new Date(run.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </div>
                  <div className="font-mono text-[8px] tracking-[0.06em] mt-0.5" style={{ color: "var(--faint)" }}>
                    {new Date(run.ran_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}
                  </div>
                </div>

                {/* Mention */}
                <div>
                  <div className="font-display font-light text-[22px] leading-none"
                    style={{ color: hasData ? scoreColor(run.aggregate_mention_rate) : "var(--faint)" }}>
                    {hasData ? formatRate(run.aggregate_mention_rate) : "—"}
                  </div>
                </div>

                {/* Citation */}
                <div>
                  <div className="font-display font-light text-[22px] leading-none"
                    style={{ color: hasData ? scoreColor(run.aggregate_citation_rate) : "var(--faint)" }}>
                    {hasData ? formatRate(run.aggregate_citation_rate) : "—"}
                  </div>
                </div>

                {/* Queries */}
                <div className="font-mono text-[10px]" style={{ color: hasData ? "var(--mute)" : "var(--neg)" }}>
                  {resultCount > 0 ? `${queryCount} / ${expectedQueries}` : "—"}
                </div>

                {/* Status */}
                <div>
                  {hasData ? (
                    <span
                      className="inline-flex items-center gap-1.5 font-mono text-[7px] tracking-[0.1em] px-2 py-0.5 rounded-sm"
                      style={{ background: "rgba(132,216,171,0.1)", color: "var(--pos)", border: "1px solid rgba(132,216,171,0.2)" }}
                    >
                      <span className="w-1 h-1 rounded-full bg-current inline-block" />OK
                    </span>
                  ) : (
                    <span
                      className="inline-flex items-center gap-1.5 font-mono text-[7px] tracking-[0.1em] px-2 py-0.5 rounded-sm"
                      style={{ background: "rgba(232,154,160,0.08)", color: "var(--neg)", border: "1px solid rgba(232,154,160,0.18)" }}
                    >
                      <span className="w-1 h-1 rounded-full bg-current inline-block" />ERROR
                    </span>
                  )}
                </div>

                {/* Report */}
                <div onClick={(e) => e.stopPropagation()}>
                  {isReported ? (
                    <button
                      className="font-mono text-[8px] tracking-[0.08em] py-1.5 px-3 cursor-default"
                      style={{ color: "var(--pos)", border: "1px solid rgba(132,216,171,0.25)" }}
                    >
                      ✓ REPORTED
                    </button>
                  ) : hasData ? (
                    <Link
                      href={`/api/admin/create-report?runId=${run.id}&clientId=${id}`}
                      className="font-mono text-[8px] tracking-[0.08em] py-1.5 px-3 transition-all duration-200 hover:text-white hover:border-[var(--ghost)]"
                      style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
                    >
                      → MAKE REPORT
                    </Link>
                  ) : (
                    <span className="font-mono text-[8px]" style={{ color: "var(--faint)", opacity: 0.4 }}>—</span>
                  )}
                </div>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
