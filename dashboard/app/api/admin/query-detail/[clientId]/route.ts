import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { pickRepresentative, extractMentionSentence } from "@/lib/mention";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ clientId: string }> }
) {
  const { clientId } = await params;
  const { searchParams } = new URL(request.url);
  const query = searchParams.get("query");
  const queryId = searchParams.get("query_id");

  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const { data: clientUser } = await supabase
    .from("client_users")
    .select("role")
    .eq("user_id", user.id)
    .single();

  if (clientUser?.role !== "admin") {
    return Response.json({ error: "Forbidden" }, { status: 403 });
  }

  if (!query && !queryId) {
    return Response.json({ error: "Missing query" }, { status: 400 });
  }

  const admin = createAdminClient();

  const { data: runs, error: runsError } = await admin
    .from("tracker_runs")
    .select("id, ran_at")
    .eq("client_id", clientId)
    .order("ran_at", { ascending: false })
    .limit(1);

  if (runsError) {
    return Response.json({ error: runsError.message }, { status: 500 });
  }

  if (!runs || runs.length === 0) {
    return Response.json({ engines: [] });
  }

  const runId = runs[0].id;

  let resultsQuery = admin
    .from("tracker_results")
    .select(
      "id, query, engine, brand_mentioned, brand_cited, citation_url, competitor_mentions, response_text, queried_at, run_number"
    )
    .eq("run_id", runId);

  resultsQuery = queryId ? resultsQuery.eq("query_id", queryId) : resultsQuery.eq("query", query);

  const { data: results, error: resultsError } = await resultsQuery;

  if (resultsError) {
    return Response.json({ error: resultsError.message }, { status: 500 });
  }

  const { data: client } = await admin
    .from("clients")
    .select("brand_name, brand_variations")
    .eq("id", clientId)
    .single();

  const brandName = client?.brand_name ?? "";
  const brandVariations = client?.brand_variations ?? [];
  const allBrandTerms = [brandName, ...brandVariations].filter(Boolean);

  const rows = results ?? [];
  const byEngine = new Map<string, typeof rows>();
  for (const r of rows) {
    const list = byEngine.get(r.engine) ?? [];
    list.push(r);
    byEngine.set(r.engine, list);
  }

  const engines = Array.from(byEngine.entries()).map(([engine, engineRows]) => {
    const total = engineRows.length;
    const mentionedCount = engineRows.filter((r) => r.brand_mentioned).length;
    const citedCount = engineRows.filter((r) => r.brand_cited).length;
    const mentioned = mentionedCount > 0;
    const cited = citedCount > 0;
    const rep = pickRepresentative(engineRows);
    const sentence = rep?.response_text
      ? extractMentionSentence(rep.response_text, allBrandTerms)
      : null;

    let citationUrl: string | null = null;
    if (rep?.brand_cited && rep.citation_url) {
      citationUrl = rep.citation_url;
    } else {
      const firstCited = engineRows.find((r) => r.brand_cited && r.citation_url);
      citationUrl = firstCited?.citation_url ?? null;
    }

    const competitorsRecommended = !mentioned ? (rep?.competitor_mentions ?? []) : [];

    return {
      engine,
      total,
      mentionedCount,
      citedCount,
      mentioned,
      cited,
      citationUrl,
      sentence,
      competitorsRecommended,
      wordings: Array.from(new Set(engineRows.map((r) => r.query))),
    };
  });

  return Response.json({ engines });
}
