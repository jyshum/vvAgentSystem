import Link from "next/link";
import { createAdminClient } from "@/lib/supabase/admin";
import type { PipelineRun, ImprovementRun } from "@/lib/improvement-types";
import { PIPELINE_STATUS_COLOR } from "@/lib/run-status";

export default async function RunsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = createAdminClient();

  const [{ data: pipelineRuns }, { data: improvementRuns }] = await Promise.all([
    supabase
      .from("pipeline_runs")
      .select("id, client_id, thread_id, run_type, status, started_at, completed_at, error_message")
      .eq("client_id", id)
      .order("started_at", { ascending: false }),
    supabase
      .from("improvement_runs")
      .select("id, thread_id, cards_generated, ran_at")
      .eq("client_id", id),
  ]);

  const runs = (pipelineRuns as PipelineRun[]) || [];
  const improvements = (improvementRuns as Pick<ImprovementRun, "id" | "thread_id" | "cards_generated" | "ran_at">[]) || [];

  const cardsByThreadId = new Map<string, number>();
  for (const imp of improvements) {
    if (imp.thread_id) cardsByThreadId.set(imp.thread_id, imp.cards_generated);
  }

  return (
    <div>
      {runs.length === 0 ? (
        <p className="font-serif italic" style={{ color: "var(--mute)" }}>
          No runs yet.
        </p>
      ) : (
        <>
          <div
            className="grid pb-2.5 border-b font-mono text-[8px] tracking-[0.14em] uppercase"
            style={{
              gridTemplateColumns: "1.5fr 1fr 1fr",
              gap: "16px",
              borderColor: "var(--hair)",
              color: "var(--faint)",
            }}
          >
            <span>DATE</span>
            <span>STATUS</span>
            <span>CARDS</span>
          </div>

          {runs.map((run) => {
            const cards = run.thread_id ? cardsByThreadId.get(run.thread_id) : undefined;
            return (
              <Link
                key={run.id}
                href={`/admin/clients/${id}/runs/${run.id}`}
                className="grid items-center py-[17px] border-b group transition-all duration-200"
                style={{
                  gridTemplateColumns: "1.5fr 1fr 1fr",
                  gap: "16px",
                  borderColor: "var(--hair)",
                }}
              >
                <div className="transition-all duration-[200ms] group-hover:pl-3" style={{ transitionTimingFunction: "cubic-bezier(.2,.8,.2,1)" }}>
                  <div className="font-serif text-[15px]" style={{ color: "var(--white)" }}>
                    {new Date(run.started_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </div>
                  <div className="font-mono text-[8px] tracking-[0.06em] mt-0.5" style={{ color: "var(--faint)" }}>
                    {new Date(run.started_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}
                  </div>
                </div>
                <div>
                  <span
                    className="font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-1"
                    style={{
                      color: PIPELINE_STATUS_COLOR[run.status] ?? "var(--mute)",
                      border: `1px solid ${PIPELINE_STATUS_COLOR[run.status] ?? "var(--mute)"}`,
                    }}
                  >
                    {run.status}
                  </span>
                </div>
                <div className="font-mono text-[10px]" style={{ color: cards != null ? "var(--white)" : "var(--faint)" }}>
                  {cards != null ? cards : "—"}
                </div>
              </Link>
            );
          })}
        </>
      )}
    </div>
  );
}
