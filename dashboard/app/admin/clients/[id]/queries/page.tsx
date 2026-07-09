import { createAdminClient } from "@/lib/supabase/admin";
import { engineAverageByQuery } from "@/lib/derive";
import { aggregatePromptScores, computePromptStability } from "@/lib/stability";
import { HeatTable, type HeatRow, type HeatCell } from "@/components/admin/HeatTable";
import type { Query } from "@/lib/types";

export default async function QueriesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const admin = createAdminClient();

  // Batch 1: independent fetches keyed only by client id
  const [{ data: runsDesc }, { data: latestImprovementRuns }, { data: queryRows }] =
    await Promise.all([
      admin
        .from("tracker_runs")
        .select("id, ran_at")
        .eq("client_id", id)
        .order("ran_at", { ascending: false })
        .limit(6),
      admin
        .from("improvement_runs")
        .select("id")
        .eq("client_id", id)
        .order("ran_at", { ascending: false })
        .limit(1),
      admin.from("queries").select("id, prompt_text, bucket").eq("client_id", id),
    ]);

  const runs = [...(runsDesc ?? [])].reverse();

  if (runs.length === 0) {
    return (
      <p className="font-serif italic" style={{ color: "var(--mute)" }}>
        No query data yet.
      </p>
    );
  }

  const runIds = runs.map((r) => r.id);
  const latestRun = runs[runs.length - 1];
  const latestImprovementRunId = latestImprovementRuns?.[0]?.id ?? null;

  const queryIdByPromptText = new Map<string, string>();
  const bucketByPromptText = new Map<string, Query["bucket"]>();
  for (const q of queryRows ?? []) {
    queryIdByPromptText.set(q.prompt_text, q.id);
    bucketByPromptText.set(q.prompt_text, q.bucket as Query["bucket"]);
  }
  const queryIds = [...queryIdByPromptText.values()];

  // Batch 2: fetches dependent on batch-1 ids
  const [{ data: promptScores }, { data: gaps }, { data: matches }, { data: pendingCards }] =
    await Promise.all([
      admin
        .from("prompt_scores")
        .select("run_id, query, bucket, llm, mention_rate, citation_rate, avg_mention_level")
        .in("run_id", runIds),
      admin
        .from("competitive_gaps")
        .select("query, competitor_data")
        .eq("run_id", latestRun.id),
      latestImprovementRunId
        ? admin
            .from("query_page_matches")
            .select("query_text, match_type, matched_page_url, similarity_score")
            .eq("run_id", latestImprovementRunId)
        : Promise.resolve({ data: null }),
      queryIds.length > 0
        ? admin
            .from("action_cards")
            .select("query_id, status")
            .in("query_id", queryIds)
            .eq("status", "pending")
        : Promise.resolve({ data: null }),
    ]);

  const scores = promptScores ?? [];

  if (scores.length === 0) {
    return (
      <p className="font-serif italic" style={{ color: "var(--mute)" }}>
        No query data yet.
      </p>
    );
  }

  // group prompt_scores by run for engine-averaging (mention_rate + citation_rate)
  const scoresByRun = new Map<string, typeof scores>();
  for (const s of scores) {
    const list = scoresByRun.get(s.run_id) ?? [];
    list.push(s);
    scoresByRun.set(s.run_id, list);
  }

  const engineAvgByRun = new Map<string, Map<string, { mention_rate: number; citation_rate: number }>>();
  for (const run of runs) {
    const runScores = scoresByRun.get(run.id) ?? [];
    engineAvgByRun.set(run.id, engineAverageByQuery(runScores));
  }

  const allQueries = new Set<string>();
  for (const s of scores) allQueries.add(s.query);
  const queryList = [...allQueries].sort();

  // cells per query, oldest -> newest
  const cellsByQuery = new Map<string, HeatCell[]>();
  for (const query of queryList) {
    const cells: HeatCell[] = runs.map((run) => {
      const avg = engineAvgByRun.get(run.id)?.get(query);
      return { runId: run.id, ranAt: run.ran_at, rate: avg ? avg.mention_rate : null };
    });
    cellsByQuery.set(query, cells);
  }

  // stability classification
  const runsDataForStability = aggregatePromptScores(scores, runs);
  const stabilityResults = computePromptStability(runsDataForStability);
  const stabilityByQuery = new Map(stabilityResults.map((r) => [r.query, r.stability_class]));

  // citedPct from latest run's engine-averaged citation_rate
  const latestEngineAvg = engineAvgByRun.get(latestRun.id) ?? new Map();

  // page matches from latest improvement run
  const pageByQuery = new Map<string, { url: string; similarity: number; weak: boolean }>();
  for (const m of matches ?? []) {
    if (!m.matched_page_url) continue;
    pageByQuery.set(m.query_text, {
      url: m.matched_page_url,
      similarity: m.similarity_score ?? 0,
      weak: m.match_type === "weak",
    });
  }

  // top competitor from latest tracker run's competitive_gaps
  const topCompetitorByQuery = new Map<string, { name: string; rate: number }>();
  for (const g of gaps ?? []) {
    const list = (g.competitor_data ?? []) as { name: string; mention_rate: number }[];
    if (list.length === 0) continue;
    const top = list.reduce((a, b) => (b.mention_rate > a.mention_rate ? b : a));
    topCompetitorByQuery.set(g.query, { name: top.name, rate: top.mention_rate });
  }

  // waiting: pending action_cards per query, via queries table's prompt_text -> id mapping
  const waitingByQueryId = new Map<string, number>();
  for (const c of pendingCards ?? []) {
    if (!c.query_id) continue;
    waitingByQueryId.set(c.query_id, (waitingByQueryId.get(c.query_id) ?? 0) + 1);
  }

  const rows: HeatRow[] = queryList.map((query) => {
    const queryId = queryIdByPromptText.get(query);
    const waiting = queryId ? waitingByQueryId.get(queryId) ?? 0 : 0;
    const citedAvg = latestEngineAvg.get(query);

    return {
      query,
      bucket: bucketByPromptText.get(query) ?? (scores.find((s) => s.query === query)?.bucket as Query["bucket"] | undefined) ?? "consideration",
      cells: cellsByQuery.get(query) ?? [],
      stability: stabilityByQuery.get(query) ?? "absent",
      citedPct: citedAvg ? citedAvg.citation_rate : null,
      page: pageByQuery.get(query) ?? null,
      topCompetitor: topCompetitorByQuery.get(query) ?? null,
      waiting,
    };
  });

  return (
    <div>
      <div className="font-mono text-[9px] tracking-[0.18em] uppercase mb-5" style={{ color: "var(--faint)" }}>
        QUERY × CYCLE
      </div>
      <HeatTable rows={rows} clientId={id} />
    </div>
  );
}
