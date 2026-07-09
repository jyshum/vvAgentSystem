import { createClient } from "@/lib/supabase/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { aggregatePromptScores, computePromptStability } from "@/lib/stability";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ clientId: string }> }
) {
  const { clientId } = await params;

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

  const admin = createAdminClient();

  const { data: runs, error: runsError } = await admin
    .from("tracker_runs")
    .select("id, ran_at")
    .eq("client_id", clientId)
    .order("ran_at", { ascending: false })
    .limit(3);

  if (runsError) {
    return Response.json({ error: runsError.message }, { status: 500 });
  }

  if (!runs || runs.length === 0) {
    return Response.json([]);
  }

  const runIds = runs.map((r) => r.id);

  const { data: scores, error: scoresError } = await admin
    .from("prompt_scores")
    .select("run_id, query_id, query, llm, mention_rate, avg_mention_level")
    .in("run_id", runIds);

  if (scoresError) {
    return Response.json({ error: scoresError.message }, { status: 500 });
  }

  const orderedRuns = [...runs].reverse();
  const runsData = aggregatePromptScores(scores || [], orderedRuns);
  const stability = computePromptStability(runsData);

  return Response.json(stability);
}
