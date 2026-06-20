export function scoreColor(rate: number, paper?: boolean): string {
  if (paper) {
    if (rate === 0) return "var(--neg-paper)";
    if (rate < 0.25) return "#c45c00";
    if (rate < 0.5) return "#8a6a00";
    return "var(--pos-paper)";
  }
  if (rate === 0) return "var(--neg)";
  if (rate < 0.25) return "#fd7e14";
  if (rate < 0.5) return "#ffc107";
  return "var(--pos)";
}

export function scoreLevel(
  rate: number
): "zero" | "low" | "mid" | "high" {
  if (rate === 0) return "zero";
  if (rate < 0.25) return "low";
  if (rate < 0.5) return "mid";
  return "high";
}

export function formatRate(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

export function formatDelta(
  current: number,
  previous: number | null
): { text: string; direction: "up" | "down" | "flat" } | null {
  if (previous === null || previous === undefined) return null;
  const diff = Math.round((current - previous) * 100);
  if (diff > 0) return { text: `+${diff}pp`, direction: "up" };
  if (diff < 0) return { text: `${diff}pp`, direction: "down" };
  return { text: "±0pp", direction: "flat" };
}

export function weekRangeLabel(weekStart: string | null): string {
  if (!weekStart) return "";
  const start = new Date(weekStart + "T00:00:00");
  if (isNaN(start.getTime())) return "";
  const end = new Date(start);
  end.setDate(end.getDate() + 6);

  const sameMonth =
    start.getMonth() === end.getMonth() &&
    start.getFullYear() === end.getFullYear();

  const startStr = start.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
  });
  const endStr = end.toLocaleDateString(
    "en-US",
    sameMonth ? { day: "numeric" } : { month: "long", day: "numeric" }
  );

  return `${startStr} – ${endStr}, ${end.getFullYear()}`;
}
