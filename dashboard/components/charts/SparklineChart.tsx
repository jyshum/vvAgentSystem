interface SparklineChartProps {
  values: (number | null)[];
  direction?: "up" | "down" | "flat" | "none";
  width?: number;
  height?: number;
}

export function SparklineChart({
  values,
  direction = "none",
  width = 160,
  height = 30,
}: SparklineChartProps) {
  const pts = values.filter(
    (v): v is number => v !== null && !isNaN(v)
  );
  const pad = 3;

  if (pts.length < 2) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="w-full"
        style={{ height }}
      >
        <text
          x="0"
          y={height - 9}
          className="font-mono text-[8px] tracking-[0.1em]"
          fill="var(--faint)"
        >
          needs 2+ data points
        </text>
      </svg>
    );
  }

  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const range = max - min || 1;
  const stepX = (width - pad * 2) / (pts.length - 1);

  const coords = pts.map((v, i) => {
    const t = (v - min) / range;
    return [pad + i * stepX, pad + (1 - t) * (height - pad * 2)] as const;
  });

  const line = coords
    .map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(" ");

  const last = coords[coords.length - 1];

  const area =
    `M${coords[0][0].toFixed(1)} ${(height - pad).toFixed(1)} ` +
    coords
      .map(([x, y]) => `L${x.toFixed(1)} ${y.toFixed(1)}`)
      .join(" ") +
    ` L${last[0].toFixed(1)} ${(height - pad).toFixed(1)} Z`;

  const strokeColor =
    direction === "up"
      ? "var(--pos)"
      : direction === "down"
        ? "var(--neg)"
        : "rgba(245,244,241,0.5)";

  const fillColor =
    direction === "up"
      ? "var(--pos)"
      : direction === "down"
        ? "var(--neg)"
        : "rgba(245,244,241,0.5)";

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="w-full"
      style={{ height }}
    >
      <path d={area} fill={fillColor} opacity={0.16} />
      <path
        d={line}
        fill="none"
        stroke={strokeColor}
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
      />
      <circle
        cx={last[0].toFixed(1)}
        cy={last[1].toFixed(1)}
        r={2.2}
        fill="var(--white)"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
