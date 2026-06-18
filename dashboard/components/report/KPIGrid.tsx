import { scoreColor, formatRate } from "@/lib/utils";
import { SparklineChart } from "@/components/charts/SparklineChart";
import type { TrackerRun } from "@/lib/types";

interface KPIGridProps {
  run: TrackerRun;
  previousRuns?: TrackerRun[];
}

export function KPIGrid({ run, previousRuns = [] }: KPIGridProps) {
  const engines = Object.entries(run.per_engine_scores);

  return (
    <div className="mt-[50px]">
      <h2
        className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
        style={{ color: "var(--mute)" }}
      >
        AI Visibility Scores
      </h2>

      <div className="grid grid-cols-2 gap-px bg-[var(--hair)] border border-[var(--hair)] mb-6">
        <ScoreCard
          label="Mention Rate"
          value={run.aggregate_mention_rate}
          history={previousRuns.map((r) => r.aggregate_mention_rate)}
        />
        <ScoreCard
          label="Citation Rate"
          value={run.aggregate_citation_rate}
          history={previousRuns.map((r) => r.aggregate_citation_rate)}
        />
      </div>

      <div
        className="grid gap-px bg-[var(--hair)] border border-[var(--hair)]"
        style={{ gridTemplateColumns: `repeat(${engines.length}, 1fr)` }}
      >
        {engines.map(([engine, scores]) => (
          <div
            key={engine}
            className="p-5 flex flex-col"
            style={{ background: "var(--ink-2)", minHeight: "120px" }}
          >
            <div
              className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3"
              style={{ color: "var(--mute)" }}
            >
              {engine}
            </div>
            <div
              className="font-serif font-light text-[32px] leading-none mb-1"
              style={{ color: scoreColor(scores.mention_rate) }}
            >
              {formatRate(scores.mention_rate)}
            </div>
            <div
              className="font-mono text-[9px] tracking-[0.1em] uppercase"
              style={{ color: "var(--faint)" }}
            >
              mention rate
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScoreCard({
  label,
  value,
  history,
}: {
  label: string;
  value: number;
  history: number[];
}) {
  const allValues = [...history, value];
  const prev = history.length > 0 ? history[history.length - 1] : null;
  const delta =
    prev !== null ? Math.round((value - prev) * 100) : null;
  const direction =
    delta === null
      ? ("none" as const)
      : delta > 0
        ? ("up" as const)
        : delta < 0
          ? ("down" as const)
          : ("flat" as const);

  return (
    <div
      className="p-5 flex flex-col"
      style={{ background: "var(--ink-2)", minHeight: "132px" }}
    >
      <div
        className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3"
        style={{ color: "var(--mute)" }}
      >
        {label}
      </div>
      <div
        className="font-serif font-light text-[40px] leading-none mb-2"
        style={{ color: scoreColor(value) }}
      >
        {formatRate(value)}
      </div>
      <div
        className="font-mono text-[10px] tracking-[0.04em]"
        style={{ color: "var(--mute)" }}
      >
        {delta !== null && (
          <>
            <span
              className="font-bold"
              style={{
                color:
                  direction === "up"
                    ? "var(--pos)"
                    : direction === "down"
                      ? "var(--neg)"
                      : "var(--mute)",
              }}
            >
              {direction === "up" ? "▲" : direction === "down" ? "▼" : "■"}
            </span>{" "}
            <span>{Math.abs(delta)}pp vs last week</span>
          </>
        )}
      </div>
      <div className="mt-auto pt-3">
        <SparklineChart values={allValues} direction={direction} />
      </div>
    </div>
  );
}
