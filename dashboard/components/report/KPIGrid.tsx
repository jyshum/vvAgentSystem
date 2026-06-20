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
        className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] mb-6"
        style={{
          color: "var(--p-mute)",
          borderBottom: "1px solid var(--p-hair)",
        }}
      >
        AI Visibility Scores
      </h2>

      <div
        className="grid grid-cols-2 gap-px mb-6"
        style={{ background: "var(--p-hair)", border: "1px solid var(--p-hair)" }}
      >
        <ScoreCard
          label="Mention Rate"
          value={run.aggregate_mention_rate}
          history={previousRuns.map((r) => r.aggregate_mention_rate)}
          primary
        />
        <ScoreCard
          label="Citation Rate"
          value={run.aggregate_citation_rate}
          history={previousRuns.map((r) => r.aggregate_citation_rate)}
        />
      </div>

      <div
        className="grid gap-px"
        style={{
          gridTemplateColumns: `repeat(${engines.length}, 1fr)`,
          background: "var(--p-hair)",
          border: "1px solid var(--p-hair)",
        }}
      >
        {engines.map(([engine, scores]) => (
          <div
            key={engine}
            className="p-5 flex flex-col"
            style={{ background: "var(--paper)", minHeight: "120px" }}
          >
            <div
              className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3"
              style={{ color: "var(--p-mute)" }}
            >
              {engine}
            </div>
            <div
              className="font-serif font-light text-[32px] leading-none mb-1"
              style={{ color: scoreColor(scores.mention_rate, true) }}
            >
              {formatRate(scores.mention_rate)}
            </div>
            <div
              className="font-mono text-[9px] tracking-[0.1em] uppercase"
              style={{ color: "var(--p-faint)" }}
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
  primary = false,
}: {
  label: string;
  value: number;
  history: number[];
  primary?: boolean;
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
      style={{ background: "var(--paper)", minHeight: "132px" }}
    >
      <div
        className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3"
        style={{ color: "var(--p-mute)" }}
      >
        {label}
      </div>
      <div
        className="font-serif font-light leading-none mb-2"
        style={{
          color: scoreColor(value, true),
          fontSize: primary ? "48px" : "40px",
        }}
      >
        {formatRate(value)}
      </div>
      <div
        className="font-mono text-[10px] tracking-[0.04em]"
        style={{ color: "var(--p-mute)" }}
      >
        {delta !== null && (
          <>
            <span
              className="font-bold"
              style={{
                color:
                  direction === "up"
                    ? "var(--pos-paper)"
                    : direction === "down"
                      ? "var(--neg-paper)"
                      : "var(--p-mute)",
              }}
            >
              {direction === "up" ? "+" : direction === "down" ? "-" : ""}
            </span>
            <span>{Math.abs(delta)}pp vs last week</span>
          </>
        )}
      </div>
      <div className="mt-auto pt-3">
        <SparklineChart values={allValues} direction={direction} paper />
      </div>
    </div>
  );
}
