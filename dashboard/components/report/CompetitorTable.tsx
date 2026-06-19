import { scoreColor, formatRate } from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

interface CompetitorTableProps {
  run: TrackerRun;
  brandName: string;
}

export function CompetitorTable({ run, brandName }: CompetitorTableProps) {
  // Exclude the brand itself from competitor list
  const competitors = Object.entries(run.competitor_scores)
    .filter(([name]) => {
      const normalized = name.toLowerCase().replace(/\s+/g, "");
      const brand = brandName.toLowerCase().replace(/\s+/g, "");
      return normalized !== brand;
    })
    .sort(([, a], [, b]) => b.mention_rate - a.mention_rate);

  if (competitors.length === 0) return null;

  return (
    <div className="mt-[50px]">
      <h2
        className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] mb-6"
        style={{
          color: "var(--p-mute)",
          borderBottom: "1px solid var(--p-hair)",
        }}
      >
        Competitor Comparison
      </h2>

      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pr-3.5 pb-2.5"
              style={{
                color: "var(--p-faint)",
                borderBottom: "1px solid var(--p-hair)",
              }}
            >
              Competitor
            </th>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pb-2.5"
              style={{
                color: "var(--p-faint)",
                borderBottom: "1px solid var(--p-hair)",
              }}
            >
              Mention Rate
            </th>
          </tr>
        </thead>
        <tbody>
          {competitors.map(([name, scores]) => (
            <tr key={name}>
              <td
                className="font-serif text-base py-2.5 pr-3.5"
                style={{
                  color: "var(--paper-ink)",
                  borderBottom: "1px solid var(--p-hair)",
                }}
              >
                {name}
              </td>
              <td
                className="py-2.5 font-mono text-sm font-medium"
                style={{
                  color: scoreColor(scores.mention_rate, true),
                  borderBottom: "1px solid var(--p-hair)",
                }}
              >
                {formatRate(scores.mention_rate)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
