export const dynamic = "force-dynamic";

import { createAdminClient } from "@/lib/supabase/admin";
import { InboxGroup, type InboxGroupData } from "@/components/approvals/InboxGroup";
import type { ReviewCardData } from "@/components/approvals/card-shared";
import { topCompetitor, rankAndGap } from "@/lib/derive";
import { formatRate, formatDelta } from "@/lib/utils";
import Link from "next/link";

/** Rows selected below match the shared ReviewCardData shape exactly. */
type CardRow = ReviewCardData;

interface TrackerRunRow {
  aggregate_mention_rate: number;
  competitor_scores: Record<string, { mention_rate: number }>;
  ran_at: string;
}

export default async function ApprovalsPage() {
  const supabase = createAdminClient();

  const { data: cardsData } = await supabase
    .from("action_cards")
    .select(
      "id, run_id, client_id, query_id, page_url, action_type, track, priority, competitive_gap, structural_score, issue, before_text, after_text, code_block, status, cms_action, auto_approved, brief, reddit_data, created_at"
    )
    .in("status", ["pending", "approved"])
    .order("created_at", { ascending: true });

  const cards = (cardsData as CardRow[]) || [];

  const reviewItems = cards.filter((c) => c.status === "pending" && !c.auto_approved);
  const autoItems = cards.filter((c) => c.auto_approved === true && c.status !== "implemented");

  const reviewByRun = new Map<string, CardRow[]>();
  for (const c of reviewItems) {
    const list = reviewByRun.get(c.run_id) ?? [];
    list.push(c);
    reviewByRun.set(c.run_id, list);
  }
  const autoByRun = new Map<string, CardRow[]>();
  for (const c of autoItems) {
    const list = autoByRun.get(c.run_id) ?? [];
    list.push(c);
    autoByRun.set(c.run_id, list);
  }

  const runIds = [...reviewByRun.keys()];

  if (runIds.length === 0) {
    return (
      <div>
        <BackLink />
        <h1
          className="font-display text-[52px] font-light leading-[0.96] mb-2"
          style={{ color: "var(--white)" }}
        >
          Approvals
        </h1>
        <p className="font-serif italic text-base mb-10" style={{ color: "var(--mute)" }}>
          0 pending action cards
        </p>
        <p className="font-serif italic text-center py-20" style={{ color: "var(--mute)" }}>
          No pending action cards.
        </p>
      </div>
    );
  }

  const clientIds = [...new Set(runIds.flatMap((rid) => (reviewByRun.get(rid) || []).map((c) => c.client_id).filter((x): x is string => !!x)))];
  const queryIds = [
    ...new Set(
      [...reviewItems, ...autoItems].map((c) => c.query_id).filter((x): x is string => !!x)
    ),
  ];

  const [runsRes, clientsRes, queriesRes] = await Promise.all([
    supabase.from("improvement_runs").select("id, client_id, ran_at, thread_id").in("id", runIds),
    clientIds.length
      ? supabase.from("clients").select("id, brand_name, cms_type").in("id", clientIds)
      : Promise.resolve({ data: [] as { id: string; brand_name: string; cms_type: string }[] }),
    queryIds.length
      ? supabase.from("queries").select("id, prompt_text").in("id", queryIds)
      : Promise.resolve({ data: [] as { id: string; prompt_text: string }[] }),
  ]);

  const runsMap = new Map<string, { id: string; client_id: string; ran_at: string; thread_id: string | null }>();
  for (const r of runsRes.data || []) runsMap.set(r.id, r);

  const clientsMap = new Map<string, { id: string; brand_name: string; cms_type: string }>();
  for (const c of clientsRes.data || []) clientsMap.set(c.id, c);

  const queriesMap = new Map<string, string>();
  for (const q of queriesRes.data || []) queriesMap.set(q.id, q.prompt_text);

  // Both maps depend only on the resolved first batch and not on each other, so
  // build them concurrently (each helper fans out its own inner Promise.all).

  // Latest-2 tracker_runs per client for the context strip.
  const buildTrackerMap = async () => {
    const map = new Map<string, TrackerRunRow[]>();
    await Promise.all(
      clientIds.map(async (clientId) => {
        const { data } = await supabase
          .from("tracker_runs")
          .select("aggregate_mention_rate, competitor_scores, ran_at")
          .eq("client_id", clientId)
          .order("ran_at", { ascending: false })
          .limit(2);
        map.set(clientId, (data as TrackerRunRow[]) || []);
      })
    );
    return map;
  };

  // Resolve thread per run: improvement_runs.thread_id, else latest matching pipeline_runs.
  const buildThreadMap = async () => {
    const map = new Map<string, string | null>();
    await Promise.all(
      runIds.map(async (runId) => {
        const run = runsMap.get(runId);
        if (!run) {
          map.set(runId, null);
          return;
        }
        if (run.thread_id) {
          map.set(runId, run.thread_id);
          return;
        }
        const { data } = await supabase
          .from("pipeline_runs")
          .select("thread_id")
          .eq("client_id", run.client_id)
          .eq("status", "awaiting_approval")
          .lte("started_at", run.ran_at)
          .order("started_at", { ascending: false })
          .limit(1);
        map.set(runId, data?.[0]?.thread_id ?? null);
      })
    );
    return map;
  };

  const [trackerByClient, threadByRun] = await Promise.all([buildTrackerMap(), buildThreadMap()]);

  // Server component rendered per-request (force-dynamic); reading the clock
  // to compute card age is intentional.
  // eslint-disable-next-line react-hooks/purity
  const now = Date.now();

  const groups: (InboxGroupData & { oldestCreatedAt: number })[] = runIds.map((runId) => {
    const run = runsMap.get(runId);
    const client = run ? clientsMap.get(run.client_id) : undefined;
    const reviewCards = (reviewByRun.get(runId) || []).slice().sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
    );
    const oldestCreatedAt = new Date(reviewCards[0].created_at).getTime();
    const waitDays = Math.floor((now - oldestCreatedAt) / 86400000);

    const trackerRuns = run ? trackerByClient.get(run.client_id) || [] : [];
    const [latest, prev] = trackerRuns;
    let contextStrip: string | null = null;
    if (latest) {
      const rate = latest.aggregate_mention_rate;
      let strip = `why you're here: ${formatRate(rate)}`;
      if (prev) {
        const delta = formatDelta(rate, prev.aggregate_mention_rate);
        if (delta) {
          strip += ` ${delta.direction === "up" ? "▲" : delta.direction === "down" ? "▼" : "±"}${delta.text}`;
        }
      }
      const comp = topCompetitor(latest.competitor_scores);
      if (comp) {
        const rank = rankAndGap(rate, latest.competitor_scores);
        if (rank.gapToLeader > 0) {
          strip += ` · losing to ${comp.name} by ${formatRate(rank.gapToLeader)}`;
        } else {
          strip += ` · leading`;
        }
      }
      contextStrip = strip;
    }

    return {
      runId,
      threadId: threadByRun.get(runId) ?? null,
      clientName: client?.brand_name || "Unknown",
      cmsType: client?.cms_type || "",
      waitDays,
      contextStrip,
      cards: reviewCards.map((c) => ({ ...c, queryText: c.query_id ? queriesMap.get(c.query_id) ?? null : null })),
      autoApproved: (autoByRun.get(runId) || []).map((c) => ({ id: c.id, action_type: c.action_type })),
      oldestCreatedAt,
    };
  });

  groups.sort((a, b) => a.oldestCreatedAt - b.oldestCreatedAt);

  return (
    <div>
      <BackLink />
      <h1
        className="font-display text-[52px] font-light leading-[0.96] mb-2"
        style={{ color: "var(--white)" }}
      >
        Approvals
      </h1>
      <p className="font-serif italic text-base mb-10" style={{ color: "var(--mute)" }}>
        {reviewItems.length} pending action card{reviewItems.length !== 1 ? "s" : ""}
      </p>
      {groups.map((g) => (
        <InboxGroup key={g.runId} group={g} />
      ))}
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/admin/clients"
      className="inline-block font-mono text-[10px] tracking-[0.1em] uppercase mb-6 transition-colors hover:text-[var(--white)]"
      style={{ color: "var(--faint)", textDecoration: "none" }}
    >
      &larr; Back to Clients
    </Link>
  );
}
