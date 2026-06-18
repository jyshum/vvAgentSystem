import { createClient } from "@/lib/supabase/server";
import Link from "next/link";
import { TriggerRunButton } from "@/components/admin/TriggerRunButton";
import { scoreColor, formatRate } from "@/lib/utils";
import type { TrackerRun, Report } from "@/lib/types";

export default async function RunsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const [{ data: runs }, { data: reports }] = await Promise.all([
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

  const allRuns = (runs as TrackerRun[]) || [];
  const reportedRunIds = new Set(
    ((reports || []) as Pick<Report, "id" | "run_id">[])
      .map((r) => r.run_id)
      .filter(Boolean) as string[]
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div className="font-mono text-[8px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          {allRuns.length} run{allRuns.length !== 1 ? "s" : ""}
        </div>
        <TriggerRunButton clientId={id} />
      </div>

      {allRuns.length === 0 ? (
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No runs yet. Click RUN TRACKER to start the first one.
        </p>
      ) : (
        <>
          {/* Table header */}
          <div
            className="grid pb-3 border-b font-mono text-[8px] tracking-[0.18em] uppercase"
            style={{
              gridTemplateColumns: "1.8fr 1fr 1fr 1fr auto",
              gap: "16px",
              borderColor: "var(--hair)",
              color: "var(--faint)",
            }}
          >
            <span>DATE</span>
            <span>MENTION</span>
            <span>CITATION</span>
            <span>REPORT</span>
            <span></span>
          </div>

          {allRuns.map((run) => (
            <div
              key={run.id}
              className="grid items-center py-4 border-b"
              style={{
                gridTemplateColumns: "1.8fr 1fr 1fr 1fr auto",
                gap: "16px",
                borderColor: "var(--hair)",
              }}
            >
              <Link
                href={`/admin/clients/${id}/runs/${run.id}`}
                className="font-mono text-[11px] tracking-[0.06em] hover:text-white transition-colors"
                style={{ color: "var(--mute)" }}
              >
                {new Date(run.ran_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}{" "}
                {new Date(run.ran_at).toLocaleTimeString("en-US", {
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </Link>
              <span
                className="font-display text-[22px] font-light"
                style={{ color: scoreColor(run.aggregate_mention_rate) }}
              >
                {formatRate(run.aggregate_mention_rate)}
              </span>
              <span
                className="font-display text-[22px] font-light"
                style={{ color: scoreColor(run.aggregate_citation_rate) }}
              >
                {formatRate(run.aggregate_citation_rate)}
              </span>
              <span className="font-mono text-[8px] tracking-[0.1em]" style={{ color: "var(--faint)" }}>
                {reportedRunIds.has(run.id) ? "report exists" : "—"}
              </span>
              <div className="flex gap-2">
                <Link
                  href={`/admin/clients/${id}/runs/${run.id}`}
                  className="font-mono text-[8px] tracking-[0.1em] uppercase py-1.5 px-3 transition-colors hover:text-white"
                  style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
                >
                  VIEW
                </Link>
                {!reportedRunIds.has(run.id) && (
                  <Link
                    href={`/api/admin/create-report?runId=${run.id}&clientId=${id}`}
                    className="font-mono text-[8px] tracking-[0.1em] uppercase py-1.5 px-3 transition-colors hover:text-white"
                    style={{ color: "var(--faint)", border: "1px solid var(--hair)" }}
                  >
                    → MAKE REPORT
                  </Link>
                )}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
