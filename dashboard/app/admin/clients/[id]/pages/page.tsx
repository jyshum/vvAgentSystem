import { createAdminClient } from "@/lib/supabase/admin";
import { PagesTable, type PageRowData, type ContentGapRow } from "@/components/pages-tab/PagesTable";

export default async function PagesTabPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const admin = createAdminClient();

  // Batch 1: independent fetches keyed only by client id.
  // (Client `queries` rows aren't needed here — query_page_matches already
  // carries query_id directly, unlike the Queries tab which groups by prompt
  // text and needs a prompt_text -> id map.)
  const [{ data: latestImprovementRuns }, { data: latestTrackerRuns }] = await Promise.all([
    admin
      .from("improvement_runs")
      .select("id")
      .eq("client_id", id)
      .order("ran_at", { ascending: false })
      .limit(1),
    admin
      .from("tracker_runs")
      .select("id")
      .eq("client_id", id)
      .order("ran_at", { ascending: false })
      .limit(1),
  ]);

  const latestImprovementRunId = latestImprovementRuns?.[0]?.id ?? null;
  const latestTrackerRunId = latestTrackerRuns?.[0]?.id ?? null;

  if (!latestImprovementRunId) {
    return (
      <p className="font-serif italic" style={{ color: "var(--mute)" }}>
        No improvement run yet — pages appear after the next scheduled run.
      </p>
    );
  }

  // Batch 2: fetches dependent on batch-1 ids
  const [
    { data: pageInventory },
    { data: citationScores },
    { data: pageMatches },
    { data: competitiveGaps },
    { data: pendingCards },
  ] = await Promise.all([
    admin
      .from("page_inventory")
      .select(
        "id, run_id, url, title, h1, first_paragraph, schema_types, word_count, last_modified, outbound_link_count, has_faq_schema, has_comparison_table"
      )
      .eq("run_id", latestImprovementRunId),
    admin
      .from("page_citation_scores")
      .select("id, run_id, page_url, structural_score, check_results, sonnet_quality, schema_status, schema_errors")
      .eq("run_id", latestImprovementRunId),
    admin
      .from("query_page_matches")
      .select("id, run_id, query_id, query_text, match_type, matched_page_url, similarity_score, bucket")
      .eq("run_id", latestImprovementRunId),
    latestTrackerRunId
      ? admin
          .from("competitive_gaps")
          .select("query_id, query, competitor_data, client_mention_rate")
          .eq("run_id", latestTrackerRunId)
      : Promise.resolve({ data: null }),
    admin
      .from("action_cards")
      .select("id, action_type, page_url, query_id, status")
      .eq("client_id", id)
      .eq("status", "pending"),
  ]);

  const scoresByUrl = new Map((citationScores ?? []).map((s) => [s.page_url, s]));
  const matchesByUrl = new Map<string, { query: string; similarity: number; weak: boolean }[]>();
  const contentGapMatches = (pageMatches ?? []).filter((m) => m.match_type === "content_gap");
  for (const m of pageMatches ?? []) {
    if (m.match_type === "content_gap" || !m.matched_page_url) continue;
    const list = matchesByUrl.get(m.matched_page_url) ?? [];
    list.push({ query: m.query_text, similarity: m.similarity_score ?? 0, weak: m.match_type === "weak" });
    matchesByUrl.set(m.matched_page_url, list);
  }

  const cardsByUrl = new Map<string, { id: string; action_type: string }[]>();
  const briefCardIdByQueryId = new Map<string, string>();
  for (const c of pendingCards ?? []) {
    if (c.page_url) {
      const list = cardsByUrl.get(c.page_url) ?? [];
      list.push({ id: c.id, action_type: c.action_type });
      cardsByUrl.set(c.page_url, list);
    }
    if (c.action_type === "content_brief" && c.query_id) {
      briefCardIdByQueryId.set(c.query_id, c.id);
    }
  }

  const gapsByQuery = new Map((competitiveGaps ?? []).map((g) => [g.query_id || g.query, g]));

  const rows: PageRowData[] = (pageInventory ?? []).map((p) => {
    const score = scoresByUrl.get(p.url) ?? null;
    return {
      url: p.url,
      title: p.title,
      score: score ? score.structural_score : null,
      schemaStatus: score ? score.schema_status : null,
      hasFaq: p.has_faq_schema,
      hasComparison: p.has_comparison_table,
      wordCount: p.word_count,
      lastModified: p.last_modified,
      queriesServed: matchesByUrl.get(p.url) ?? [],
      checks: score ? score.check_results : null,
      schemaErrors: score ? score.schema_errors ?? [] : [],
      sonnet: score ? score.sonnet_quality : null,
      waitingCards: cardsByUrl.get(p.url) ?? [],
    };
  });

  const gaps: ContentGapRow[] = contentGapMatches.map((m) => {
    const gapRow = gapsByQuery.get(m.query_id) ?? gapsByQuery.get(m.query_text);
    const competitors = (gapRow?.competitor_data ?? []) as { name: string; mention_rate: number }[];
    let topCompetitor: string | null = null;
    let gap: number | null = null;
    if (gapRow && competitors.length > 0) {
      const top = competitors.reduce((a, b) => (b.mention_rate > a.mention_rate ? b : a));
      topCompetitor = top.name;
      gap = top.mention_rate - (gapRow.client_mention_rate ?? 0);
    }
    return {
      query: m.query_text,
      topCompetitor,
      gap,
      briefCardId: briefCardIdByQueryId.get(m.query_id) ?? null,
    };
  });

  return (
    <div>
      <div className="font-mono text-[9px] tracking-[0.18em] uppercase mb-5" style={{ color: "var(--faint)" }}>
        PAGE INVENTORY
      </div>
      <PagesTable rows={rows} gaps={gaps} />
    </div>
  );
}
