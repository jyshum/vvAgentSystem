import { scoreColor, formatRate } from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

interface CompetitorTableProps {
  run: TrackerRun;
  brandName: string;
}

export function CompetitorTable({ run, brandName }: CompetitorTableProps) {
  const competitors = Object.entries(run.competitor_scores).sort(
    ([, a], [, b]) => b.mention_rate - a.mention_rate
  );

  if (competitors.length === 0) return null;

  return (
    <div className="mt-[50px]">
      <h2
        className="font-mono text-xs font-normal tracking-[0.14em] uppercase pb-[11px] border-b border-[var(--hair)] mb-6"
        style={{ color: "var(--mute)" }}
      >
        Competitor Comparison
      </h2>

      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pr-3.5 pb-2.5 border-b border-[var(--hair)]"
              style={{ color: "var(--mute)" }}
            >
              Brand / Competitor
            </th>
            <th
              className="font-mono text-[10px] tracking-[0.12em] uppercase text-left py-0 pb-2.5 border-b border-[var(--hair)]"
              style={{ color: "var(--mute)" }}
            >
              Mention Rate
            </th>
          </tr>
        </thead>
        <tbody>
          <tr style={{ background: "rgba(245,244,241,0.04)" }}>
            <td
              className="font-serif text-base py-2.5 pr-3.5 border-b border-[var(--hair)]"
              style={{ color: "var(--white)" }}
            >
              <strong>{brandName}</strong>
            </td>
            <td className="py-2.5 border-b border-[var(--hair)]">
              <span
                className="font-bold"
                style={{
                  color: scoreColor(run.aggregate_mention_rate),
                }}
              >
                {formatRate(run.aggregate_mention_rate)}
              </span>
            </td>
          </tr>
          {competitors.map(([name, scores]) => (
            <tr key={name}>
              <td
                className="font-serif text-base py-2.5 pr-3.5 border-b border-[var(--hair)]"
                style={{ color: "var(--white)" }}
              >
                {name}
              </td>
              <td className="py-2.5 border-b border-[var(--hair)]">
                <span
                  className="font-bold"
                  style={{ color: scoreColor(scores.mention_rate) }}
                >
                  {formatRate(scores.mention_rate)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
