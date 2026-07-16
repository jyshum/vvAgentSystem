import { createAdminClient } from "@/lib/supabase/admin";
import { engineAverageByQuery } from "@/lib/derive";
import { aggregatePromptScores, computePromptStability } from "@/lib/stability";
import { HeatTable, type HeatRow, type HeatCell } from "@/components/admin/HeatTable";
import type { Query } from "@/lib/types";

export default async function QueriesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const admin = createAdminClient();

  // Batch 1: independent fetches keyed only by client id
  const [{ data: runsDesc }, { data: queryRows }] = await Promise.all([
      admin
        .from("tracker_runs")
        .select("id, ran_at, query_set_changed")
        .eq("client_id", id)
        .order("ran_at", { ascending: false })
        .limit(6),
      admin.from("queries").select("id, prompt_text, bucket, paraphrases, version").eq("client_id", id),
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
  const queryMetaById = new Map<string, Pick<Query, "id" | "prompt_text" | "bucket" | "paraphrases" | "version">>();
  const queryIdByPromptText = new Map<string, string>();
  for (const q of queryRows ?? []) {
    queryIdByPromptText.set(q.prompt_text, q.id);
    queryMetaById.set(q.id, q as Pick<Query, "id" | "prompt_text" | "bucket" | "paraphrases" | "version">);
  }
  // Batch 2: fetches dependent on batch-1 ids
  const [{ data: promptScores }, { data: gaps }] =
    await Promise.all([
      admin
        .from("prompt_scores")
        .select("run_id, query_id, query, bucket, llm, mention_rate, citation_rate, avg_mention_level")
        .in("run_id", runIds),
      admin
        .from("competitive_gaps")
        .select("query_id, query, competitor_data")
        .eq("run_id", latestRun.id),
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

  const allQueryKeys = new Set<string>();
  const labelByKey = new Map<string, string>();
  const bucketByKey = new Map<string, Query["bucket"]>();
  for (const s of scores) {
    const key = s.query_id || s.query;
    allQueryKeys.add(key);
    labelByKey.set(key, queryMetaById.get(s.query_id || "")?.prompt_text || s.query);
    bucketByKey.set(key, (queryMetaById.get(s.query_id || "")?.bucket || s.bucket || "consideration") as Query["bucket"]);
  }
  const queryList = [...allQueryKeys].sort((a, b) => (labelByKey.get(a) || a).localeCompare(labelByKey.get(b) || b));

  // cells per query, oldest -> newest
  const cellsByQuery = new Map<string, HeatCell[]>();
  for (const query of queryList) {
    const cells: HeatCell[] = runs.map((run) => {
      const avg = engineAvgByRun.get(run.id)?.get(query);
      return { runId: run.id, ranAt: run.ran_at, rate: avg ? avg.mention_rate : null, querySetChanged: run.query_set_changed === true };
    });
    cellsByQuery.set(query, cells);
  }

  // stability classification
  const runsDataForStability = aggregatePromptScores(scores, runs);
  const stabilityResults = computePromptStability(runsDataForStability);
  const stabilityByQuery = new Map(stabilityResults.map((r) => [r.query_id || r.query, r.stability_class]));

  // citedPct from latest run's engine-averaged citation_rate
  const latestEngineAvg = engineAvgByRun.get(latestRun.id) ?? new Map();

  // top competitor from latest tracker run's competitive_gaps
  const topCompetitorByQuery = new Map<string, { name: string; rate: number }>();
  for (const g of gaps ?? []) {
    const list = (g.competitor_data ?? []) as { name: string; mention_rate: number }[];
    if (list.length === 0) continue;
    const top = list.reduce((a, b) => (b.mention_rate > a.mention_rate ? b : a));
    topCompetitorByQuery.set(g.query_id || g.query, { name: top.name, rate: top.mention_rate });
  }

  const rows: HeatRow[] = queryList.map((query) => {
    const queryId = queryMetaById.has(query) ? query : queryIdByPromptText.get(query) || null;
    const meta = queryId ? queryMetaById.get(queryId) : undefined;
    const citedAvg = latestEngineAvg.get(query);

    return {
      queryId,
      query: meta?.prompt_text || labelByKey.get(query) || query,
      paraphrases: meta?.paraphrases || [],
      version: meta?.version,
      bucket: bucketByKey.get(query) ?? "consideration",
      cells: cellsByQuery.get(query) ?? [],
      stability: stabilityByQuery.get(query) ?? "absent",
      citedPct: citedAvg ? citedAvg.citation_rate : null,
      topCompetitor: topCompetitorByQuery.get(query) ?? null,
    };
  });

  return (
    <div>
      <div className="mb-5">
        <div className="font-mono text-[9px] tracking-[0.18em] uppercase" style={{ color: "var(--faint)" }}>
          QUERY × CYCLE
        </div>
        <div className="font-serif italic text-[11px] mt-1" style={{ color: "var(--faint)" }}>
          cell % = intent mention rate averaged equally across engines · cited % = of responses that mentioned the brand
        </div>
      </div>
      <HeatTable rows={rows} clientId={id} />
    </div>
  );
}
