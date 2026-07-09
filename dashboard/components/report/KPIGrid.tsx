import { scoreColor, formatRate, getMentionLevelColor, formatMentionLevel, getMentionLevelLabel } from "@/lib/utils";
import { SparklineChart } from "@/components/charts/SparklineChart";
import type { TrackerRun } from "@/lib/types";

interface KPIGridProps {
  run: TrackerRun;
  previousRuns?: TrackerRun[];
}

export function KPIGrid({ run, previousRuns = [] }: KPIGridProps) {
  const engines = Object.entries(run.per_engine_scores);
  const prev = previousRuns.length > 0 ? previousRuns[previousRuns.length - 1] : null;
  const primaryRate = run.non_branded_mention_rate ?? run.aggregate_mention_rate;
  const previousPrimaryRate = prev ? prev.non_branded_mention_rate ?? prev.aggregate_mention_rate : null;

  const mentionHistory = previousRuns.map((r) => r.non_branded_mention_rate ?? r.aggregate_mention_rate);
  const levelHistory = previousRuns.map((r) => r.aggregate_avg_mention_level);

  const mentionDelta = prev
    ? Math.round((primaryRate - (previousPrimaryRate ?? 0)) * 100)
    : null;
  const levelDelta = prev
    ? +(run.aggregate_avg_mention_level - prev.aggregate_avg_mention_level).toFixed(1)
    : null;

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

      {/* Hero pair */}
      <div
        className="grid grid-cols-2 gap-px mb-6"
        style={{ background: "var(--p-hair)", border: "1px solid var(--p-hair)" }}
      >
        <div className="p-5 flex flex-col" style={{ background: "var(--paper)", minHeight: "132px" }}>
          <div className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3" style={{ color: "var(--p-mute)" }}>
            Non-Branded Mention Rate
          </div>
          <div className="font-serif font-light text-[48px] leading-none mb-2" style={{ color: scoreColor(primaryRate, true) }}>
            {formatRate(primaryRate)}
          </div>
          {mentionDelta !== null && (
            <div className="font-mono text-[10px] tracking-[0.04em]" style={{ color: "var(--p-mute)" }}>
              <span className="font-bold" style={{ color: mentionDelta > 0 ? "var(--pos-paper)" : mentionDelta < 0 ? "var(--neg-paper)" : "var(--p-mute)" }}>
                {mentionDelta > 0 ? "+" : ""}
              </span>
              <span>{Math.abs(mentionDelta)}pp vs last week</span>
            </div>
          )}
          <div className="font-mono text-[9px] tracking-[0.06em]" style={{ color: "var(--p-faint)" }}>
            Branded deferred
          </div>
          <div className="mt-auto pt-3">
            <SparklineChart
              values={[...mentionHistory, primaryRate]}
              direction={mentionDelta === null ? "none" : mentionDelta > 0 ? "up" : mentionDelta < 0 ? "down" : "flat"}
              paper
            />
          </div>
        </div>

        <div className="p-5 flex flex-col" style={{ background: "var(--paper)", minHeight: "132px" }}>
          <div className="font-mono text-[11px] tracking-[0.12em] uppercase mb-3" style={{ color: "var(--p-mute)" }}>
            Avg Mention Level
          </div>
          <div className="font-serif font-light text-[48px] leading-none mb-1" style={{ color: getMentionLevelColor(run.aggregate_avg_mention_level, true) }}>
            {formatMentionLevel(run.aggregate_avg_mention_level)}
          </div>
          <div className="font-mono text-[9px] tracking-[0.08em] mb-2" style={{ color: getMentionLevelColor(run.aggregate_avg_mention_level, true) }}>
            {getMentionLevelLabel(Math.round(run.aggregate_avg_mention_level))}
          </div>
          {levelDelta !== null && (
            <div className="font-mono text-[10px] tracking-[0.04em]" style={{ color: "var(--p-mute)" }}>
              <span className="font-bold" style={{ color: levelDelta > 0 ? "var(--pos-paper)" : levelDelta < 0 ? "var(--neg-paper)" : "var(--p-mute)" }}>
                {levelDelta > 0 ? "+" : ""}
              </span>
              <span>{Math.abs(levelDelta)} vs last week</span>
            </div>
          )}
          <div className="mt-auto pt-3">
            <SparklineChart
              values={[...levelHistory, run.aggregate_avg_mention_level]}
              direction={levelDelta === null ? "none" : levelDelta > 0 ? "up" : levelDelta < 0 ? "down" : "flat"}
              paper
            />
          </div>
        </div>
      </div>

      {/* Engine grid */}
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
            className="p-5 flex flex-col gap-2"
            style={{ background: "var(--paper)", minHeight: "120px" }}
          >
            <div className="font-mono text-[11px] tracking-[0.12em] uppercase mb-2" style={{ color: "var(--p-mute)" }}>
              {engine}
            </div>
            <div className="flex justify-between items-center">
              <span className="font-mono text-[9px] tracking-[0.06em]" style={{ color: "var(--p-faint)" }}>Mention</span>
              <span className="font-serif font-light text-[24px] leading-none" style={{ color: scoreColor(scores.mention_rate, true) }}>
                {formatRate(scores.mention_rate)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="font-mono text-[9px] tracking-[0.06em]" style={{ color: "var(--p-faint)" }}>Level</span>
              <span className="font-serif font-light text-[24px] leading-none" style={{ color: getMentionLevelColor(scores.avg_mention_level, true) }}>
                {formatMentionLevel(scores.avg_mention_level)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="font-mono text-[9px] tracking-[0.06em]" style={{ color: "var(--p-faint)" }}>Citation</span>
              <span className="font-mono text-[14px]" style={{ color: "var(--paper-ink)" }}>
                {formatRate(scores.citation_rate)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
