import { Card } from "@/components/ui/Card";
import { formatRate } from "@/lib/utils";
import type { TrackerRun } from "@/lib/types";

interface TrendChartProps {
  runs: TrackerRun[];
}

export function TrendChart({ runs }: TrendChartProps) {
  if (runs.length < 2) return null;

  const sorted = [...runs].sort(
    (a, b) => new Date(a.ran_at).getTime() - new Date(b.ran_at).getTime()
  );

  const values = sorted.map((r) => r.aggregate_mention_rate);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 0.01;

  const W = 800;
  const H = 200;
  const pad = 30;
  const stepX = (W - pad * 2) / (values.length - 1);

  const coords = values.map((v, i) => {
    const t = (v - min) / range;
    return [pad + i * stepX, pad + (1 - t) * (H - pad * 2)] as const;
  });

  const line = coords
    .map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(" ");

  const last = coords[coords.length - 1];

  return (
    <Card elevated className="p-6 mb-10">
      <div
        className="font-mono text-[11px] tracking-[0.12em] uppercase mb-4"
        style={{ color: "var(--mute)" }}
      >
        Visibility Trend
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 200 }}>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const y = pad + (1 - t) * (H - pad * 2);
          const val = min + t * range;
          return (
            <g key={t}>
              <line
                x1={pad}
                x2={W - pad}
                y1={y}
                y2={y}
                stroke="var(--hair)"
                strokeWidth={1}
              />
              <text
                x={pad - 8}
                y={y + 3}
                textAnchor="end"
                className="font-mono"
                style={{ fontSize: 9, fill: "var(--faint)" }}
              >
                {formatRate(val)}
              </text>
            </g>
          );
        })}

        <path
          d={line}
          fill="none"
          stroke="var(--pos)"
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
        />

        <circle
          cx={last[0]}
          cy={last[1]}
          r={4}
          fill="var(--white)"
          vectorEffect="non-scaling-stroke"
        />

        {sorted.map((r, i) => {
          const x = pad + i * stepX;
          const date = new Date(r.ran_at);
          const label = date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          });
          return (
            <text
              key={r.id}
              x={x}
              y={H - 5}
              textAnchor="middle"
              className="font-mono"
              style={{ fontSize: 9, fill: "var(--faint)" }}
            >
              {label}
            </text>
          );
        })}
      </svg>
    </Card>
  );
}
