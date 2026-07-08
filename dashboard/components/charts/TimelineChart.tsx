import { formatRate } from "@/lib/utils";

interface TimelinePoint {
  label: string;
  value: number;
}

interface TimelineChartProps {
  series: TimelinePoint[];
  competitor?: { name: string; series: (number | null)[] };
  height?: number;
}

const WIDTH = 640;
const PAD = 24;
const PAD_BOTTOM = 40;

export function TimelineChart({ series, competitor, height = 180 }: TimelineChartProps) {
  if (series.length < 2) {
    return (
      <p className="font-serif italic text-base" style={{ color: "var(--mute)" }}>
        needs 2+ cycles
      </p>
    );
  }

  const values = series.map((p) => p.value);
  const max = Math.max(...values, ...(competitor?.series.filter((v): v is number => v !== null) ?? []), 0.0001);
  const range = max;

  const innerW = WIDTH - PAD * 2;
  const innerH = height - PAD - PAD_BOTTOM;
  const stepX = series.length > 1 ? innerW / (series.length - 1) : 0;

  const xAt = (i: number) => PAD + i * stepX;
  const yAt = (v: number) => PAD + (1 - v / range) * innerH;

  const clientCoords = series.map((p, i) => [xAt(i), yAt(p.value)] as const);

  // Build competitor segments, skipping null gaps.
  const compSegments: { x: number; y: number }[][] = [];
  let lastNonNullIdx = -1;
  if (competitor) {
    let current: { x: number; y: number }[] = [];
    competitor.series.forEach((v, i) => {
      if (v === null) {
        if (current.length > 1) compSegments.push(current);
        current = [];
        return;
      }
      current.push({ x: xAt(i), y: yAt(v) });
      lastNonNullIdx = i;
    });
    if (current.length > 1) compSegments.push(current);
  }

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${height}`}
      preserveAspectRatio="none"
      className="w-full"
      style={{ height }}
    >
      {compSegments.map((seg, i) => (
        <polyline
          key={i}
          points={seg.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ")}
          fill="none"
          stroke="var(--faint)"
          strokeWidth={1.5}
          strokeDasharray="4 3"
        />
      ))}
      {competitor && lastNonNullIdx >= 0 && (
        <text
          x={xAt(lastNonNullIdx)}
          // Below the point (client value labels sit above theirs), clamped
          // inside the viewBox so the two never collide at the same x.
          y={Math.min(
            Math.max(yAt(competitor.series[lastNonNullIdx] as number) + 12, 10),
            height - PAD_BOTTOM + 10
          )}
          fontSize={8}
          fontFamily="var(--mono)"
          fill="var(--faint)"
          textAnchor="middle"
        >
          {competitor.name}
        </text>
      )}

      <polyline
        points={clientCoords.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ")}
        fill="none"
        stroke="var(--white)"
        strokeWidth={1.5}
      />
      {clientCoords.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={2.5} fill="var(--white)" />
      ))}
      {series.map((p, i) => (
        <text
          key={`val-${i}`}
          x={xAt(i)}
          y={yAt(p.value) - 8}
          fontSize={8}
          fontFamily="var(--mono)"
          fill="var(--mute)"
          textAnchor="middle"
        >
          {formatRate(p.value)}
        </text>
      ))}
      {series.map((p, i) => (
        <text
          key={`label-${i}`}
          x={xAt(i)}
          y={height - PAD_BOTTOM + 16}
          fontSize={8}
          fontFamily="var(--mono)"
          fill="var(--faint)"
          textAnchor="middle"
        >
          {p.label}
        </text>
      ))}
    </svg>
  );
}
