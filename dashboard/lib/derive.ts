export interface CompetitorPick { name: string; rate: number }
export interface RankResult { rank: number; total: number; gapToLeader: number }
export interface QueryMove { query: string; before: number; after: number; change: number }
export interface EngineAvg { mention_rate: number; citation_rate: number }
export type OpsBadgeKind = "error" | "waiting" | "measuring" | "healthy" | "not_run";
export interface OpsBadgeResult { kind: OpsBadgeKind; label: string }

type CompetitorScores = Record<string, { mention_rate: number }> | null | undefined;
interface ScoreRow { query_id?: string | null; query: string; llm: string; mention_rate: number; citation_rate: number }

function round4(n: number): number {
  return Math.round(n * 10000) / 10000;
}

export function topCompetitor(scores: CompetitorScores): CompetitorPick | null {
  const entries = Object.entries(scores ?? {});
  if (entries.length === 0) return null;
  const [name, s] = entries.reduce((a, b) => (b[1].mention_rate > a[1].mention_rate ? b : a));
  return { name, rate: s.mention_rate };
}

export function rankAndGap(clientRate: number, scores: CompetitorScores): RankResult {
  const rates = Object.values(scores ?? {}).map((s) => s.mention_rate);
  const rank = 1 + rates.filter((r) => r > clientRate).length;
  const maxRate = rates.length ? Math.max(...rates) : 0;
  const gapToLeader = round4(Math.max(0, maxRate - clientRate));
  return { rank, total: rates.length + 1, gapToLeader };
}

export function engineAverageByQuery(rows: ScoreRow[]): Map<string, EngineAvg> {
  const grouped = new Map<string, ScoreRow[]>();
  for (const r of rows) {
    const key = r.query_id || r.query;
    const list = grouped.get(key) ?? [];
    list.push(r);
    grouped.set(key, list);
  }
  const out = new Map<string, EngineAvg>();
  for (const [key, list] of grouped) {
    out.set(key, {
      mention_rate: round4(list.reduce((s, x) => s + x.mention_rate, 0) / list.length),
      citation_rate: round4(list.reduce((s, x) => s + x.citation_rate, 0) / list.length),
    });
  }
  return out;
}

export function biggestMovers(latest: ScoreRow[], previous: ScoreRow[] | null, n = 2): QueryMove[] {
  if (!previous) return [];
  const latestAvg = engineAverageByQuery(latest);
  const prevAvg = engineAverageByQuery(previous);
  const labelByKey = new Map(latest.map((row) => [row.query_id || row.query, row.query]));
  const moves: QueryMove[] = [];
  for (const [key, cur] of latestAvg) {
    const before = prevAvg.get(key)?.mention_rate ?? 0;
    const change = round4(cur.mention_rate - before);
    moves.push({ query: labelByKey.get(key) || key, before, after: cur.mention_rate, change });
  }
  moves.sort((a, b) => Math.abs(b.change) - Math.abs(a.change));
  return moves.slice(0, n).filter((m) => m.change !== 0);
}

export function opsBadge(input: {
  latestPipelineStatus: string | null;
  pendingCount: number;
  oldestPendingDays: number | null;
  measuring: number;
  hasRun: boolean;
}): OpsBadgeResult {
  if (!input.hasRun) return { kind: "not_run", label: "NOT RUN YET" };
  if (input.latestPipelineStatus === "error") return { kind: "error", label: "RUN ERROR" };
  if (input.pendingCount > 0) {
    const age = input.oldestPendingDays != null ? ` · ${input.oldestPendingDays}D` : "";
    return { kind: "waiting", label: `${input.pendingCount} CARDS${age}` };
  }
  if (input.measuring > 0) return { kind: "measuring", label: "MEASURING" };
  return { kind: "healthy", label: "HEALTHY" };
}

export function aggregateCitationRate(rows: ScoreRow[]): number | null {
  const mentioned = rows.filter((r) => r.mention_rate > 0);
  if (mentioned.length === 0) return null;
  return round4(mentioned.reduce((s, r) => s + r.citation_rate, 0) / mentioned.length);
}

export function measuringCount(
  cards: { status: string; created_at: string }[],
  latestTrackerRanAt: string | null
): number {
  if (!latestTrackerRanAt) return 0;
  const cutoff = new Date(latestTrackerRanAt).getTime();
  return cards.filter(
    (c) => c.status === "implemented" && new Date(c.created_at).getTime() > cutoff
  ).length;
}
