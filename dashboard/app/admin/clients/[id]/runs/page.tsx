import { createAdminClient } from "@/lib/supabase/admin";
import { TriggerRunButton } from "@/components/admin/TriggerRunButton";
import { RunRow } from "@/components/admin/RunRow";
import type { TrackerRun, Report, Client } from "@/lib/types";

export default async function RunsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = createAdminClient();

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
  const reportByRunId: Record<string, string> = {};
  ((reports || []) as Pick<Report, "id" | "run_id">[]).forEach((r) => {
    if (r.run_id) reportByRunId[r.run_id] = r.id;
  });
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
        <TriggerRunButton clientId={id} latestRunAt={allRuns[0]?.ran_at ?? null} />
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
              gridTemplateColumns: "1.5fr 1fr 1fr 80px 1fr 190px",
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
            <span>ACTIONS</span>
          </div>

          {allRuns.map((run) => (
            <RunRow
              key={run.id}
              run={run}
              clientId={id}
              reportId={reportByRunId[run.id] ?? null}
              expectedQueries={expectedQueries}
              resultCount={runResultCounts[run.id] ?? 0}
            />
          ))}
        </>
      )}
    </div>
  );
}
