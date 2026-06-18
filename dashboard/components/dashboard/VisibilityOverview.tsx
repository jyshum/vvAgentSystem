import { Card } from "@/components/ui/Card";
import { scoreColor, formatRate, formatDelta } from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

interface VisibilityOverviewProps {
  latestRun: TrackerRun | null;
  previousRun: TrackerRun | null;
  totalReports: number;
}

export function VisibilityOverview({
  latestRun,
  previousRun,
  totalReports,
}: VisibilityOverviewProps) {
  const mentionRate = latestRun?.aggregate_mention_rate ?? 0;
  const citationRate = latestRun?.aggregate_citation_rate ?? 0;
  const engineCount = latestRun
    ? Object.keys(latestRun.per_engine_scores).length
    : 0;

  const mentionDelta = formatDelta(
    mentionRate,
    previousRun?.aggregate_mention_rate ?? null
  );
  const citationDelta = formatDelta(
    citationRate,
    previousRun?.aggregate_citation_rate ?? null
  );

  const cards = [
    {
      label: "Overall Visibility",
      value: formatRate(mentionRate),
      color: scoreColor(mentionRate),
      delta: mentionDelta,
    },
    {
      label: "Citation Rate",
      value: formatRate(citationRate),
      color: scoreColor(citationRate),
      delta: citationDelta,
    },
    {
      label: "Engines Tracked",
      value: String(engineCount),
      color: "var(--white)",
      delta: null,
    },
    {
      label: "Reports Available",
      value: String(totalReports),
      color: "var(--white)",
      delta: null,
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-4 mb-10">
      {cards.map((card) => (
        <Card key={card.label} elevated className="p-6 text-center">
          <div
            className="font-mono text-[10.5px] tracking-[0.2em] uppercase mb-2"
            style={{ color: "var(--mute)" }}
          >
            {card.label}
          </div>
          <div
            className="font-serif text-[56px] leading-none my-2"
            style={{ color: card.color }}
          >
            {card.value}
          </div>
          {card.delta && (
            <div
              className="font-mono text-[10px] tracking-[0.04em]"
              style={{
                color:
                  card.delta.direction === "up"
                    ? "var(--pos)"
                    : card.delta.direction === "down"
                      ? "var(--neg)"
                      : "var(--mute)",
              }}
            >
              {card.delta.direction === "up"
                ? "▲"
                : card.delta.direction === "down"
                  ? "▼"
                  : "■"}{" "}
              {card.delta.text} vs last week
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
