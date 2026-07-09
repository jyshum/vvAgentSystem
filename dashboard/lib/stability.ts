export type StabilityClass = "locked_in" | "gaining" | "declining" | "volatile" | "absent";

interface QueryScores {
  query_id: string | null;
  query: string;
  mention_rate: number;
  avg_mention_level: number;
}

interface RunData {
  run_id: string;
  ran_at: string;
  queries: Record<string, QueryScores>;
}

export interface PromptStabilityResult {
  query_id: string | null;
  query: string;
  stability_class: StabilityClass;
  current_mention_rate: number;
  current_avg_level: number;
  trend: {
    run_id: string;
    ran_at: string;
    mention_rate: number;
    avg_mention_level: number;
  }[];
}

function classify(rates: number[], levels: number[]): StabilityClass {
  const n = rates.length;

  if (rates.every((r) => r === 0)) {
    return "absent";
  }

  if (n >= 3 && rates.every((r) => r >= 0.7)) {
    const levelRange = Math.max(...levels) - Math.min(...levels);
    if (levelRange <= 0.5) {
      return "locked_in";
    }
  }

  if (n >= 3) {
    const rateDiffs = [];
    for (let i = 0; i < n - 1; i++) {
      rateDiffs.push(rates[i + 1] - rates[i]);
    }
    const signs = rateDiffs.map((d) => (d > 0 ? 1 : d < 0 ? -1 : 0));
    const nonzeroSigns = signs.filter((s) => s !== 0);
    const uniqueSigns = new Set(nonzeroSigns);
    if (uniqueSigns.size > 1) {
      return "volatile";
    }
  }

  if (n >= 2) {
    const rateDelta = rates[n - 1] - rates[0];
    const levelDelta = levels[n - 1] - levels[0];

    const rateGaining = rateDelta >= 0.1;
    const rateDeclining = rateDelta <= -0.1;
    const levelGaining = levelDelta >= 0.5;
    const levelDeclining = levelDelta <= -0.5;

    if (rateGaining || (!rateDeclining && levelGaining)) {
      return "gaining";
    }

    if (rateDeclining || (!rateGaining && levelDeclining)) {
      return "declining";
    }
  }

  return "volatile";
}

export function aggregatePromptScores(
  promptScores: { run_id: string; query_id?: string | null; query: string; llm: string; mention_rate: number; avg_mention_level: number }[],
  runs: { id: string; ran_at: string }[]
): RunData[] {
  const byRunQuery: Record<string, Record<string, typeof promptScores>> = {};

  for (const ps of promptScores) {
    const key = ps.query_id || ps.query;
    if (!byRunQuery[ps.run_id]) byRunQuery[ps.run_id] = {};
    if (!byRunQuery[ps.run_id][key]) byRunQuery[ps.run_id][key] = [];
    byRunQuery[ps.run_id][key].push(ps);
  }

  return runs.map((run) => {
    const queries: Record<string, QueryScores> = {};
    const runScores = byRunQuery[run.id] || {};

    for (const [query, scores] of Object.entries(runScores)) {
      const n = scores.length;
      const avgRate = scores.reduce((s, x) => s + x.mention_rate, 0) / n;
      const label = scores[scores.length - 1]?.query || query;
      const queryId = scores.find((x) => x.query_id)?.query_id || null;

      const totalWeight = scores.reduce((s, x) => s + x.mention_rate, 0);
      const avgLevel =
        totalWeight > 0
          ? scores.reduce((s, x) => s + x.avg_mention_level * x.mention_rate, 0) / totalWeight
          : 0;

      queries[query] = {
        query_id: queryId,
        query: label,
        mention_rate: avgRate,
        avg_mention_level: avgLevel,
      };
    }

    return { run_id: run.id, ran_at: run.ran_at, queries };
  });
}

export function computePromptStability(runsData: RunData[]): PromptStabilityResult[] {
  if (runsData.length === 0) return [];

  const allQueries = new Set<string>();
  for (const run of runsData) {
    for (const q of Object.keys(run.queries)) {
      allQueries.add(q);
    }
  }

  const results: PromptStabilityResult[] = [];

  for (const query of [...allQueries].sort()) {
    const rates: number[] = [];
    const levels: number[] = [];
    const trend: PromptStabilityResult["trend"] = [];
    let label = query;
    let queryId: string | null = null;

    for (const run of runsData) {
      const qData = run.queries[query];
      if (qData) {
        label = qData.query;
        queryId = qData.query_id;
      }
      const metrics = qData || { mention_rate: 0, avg_mention_level: 0 };
      rates.push(metrics.mention_rate);
      levels.push(metrics.avg_mention_level);
      trend.push({
        run_id: run.run_id,
        ran_at: run.ran_at,
        mention_rate: metrics.mention_rate,
        avg_mention_level: metrics.avg_mention_level,
      });
    }

    results.push({
      query_id: queryId,
      query: label,
      stability_class: classify(rates, levels),
      current_mention_rate: rates[rates.length - 1],
      current_avg_level: levels[levels.length - 1],
      trend,
    });
  }

  return results;
}
