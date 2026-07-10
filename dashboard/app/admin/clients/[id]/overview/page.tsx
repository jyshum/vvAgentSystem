import { createAdminClient } from "@/lib/supabase/admin";
import { TimelineChart } from "@/components/charts/TimelineChart";
import { topCompetitor } from "@/lib/derive";
import { BUCKET_LABELS, contentAuthorityScore, productVisibilityScore } from "@/lib/intent-labels";
import { formatRate } from "@/lib/utils";
import type { Client, TrackerRun } from "@/lib/types";

type RunRow = Pick<
  TrackerRun,
  "id" | "ran_at" | "aggregate_mention_rate" | "non_branded_mention_rate" | "bucket_scores" | "competitor_scores" | "gsc_clicks" | "gsc_impressions" | "gsc_ctr" | "query_set_changed"
>;

export default async function OverviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = createAdminClient();
  const [{ data: runs }, { data: client }] = await Promise.all([
    supabase
      .from("tracker_runs")
      .select("id, ran_at, aggregate_mention_rate, non_branded_mention_rate, bucket_scores, competitor_scores, gsc_clicks, gsc_impressions, gsc_ctr, query_set_changed")
      .eq("client_id", id)
      .order("ran_at", { ascending: true }),
    supabase.from("clients").select("gsc_site_url").eq("id", id).single(),
  ]);

  const allRuns = (runs as RunRow[]) || [];

  if (allRuns.length === 0) {
    return (
      <p className="font-serif italic" style={{ color: "var(--mute)" }}>
        No runs yet.
      </p>
    );
  }

  const history = allRuns
    .map((run) => ({ run, productVisibility: productVisibilityScore(run) }))
    .filter((entry): entry is { run: RunRow; productVisibility: NonNullable<ReturnType<typeof productVisibilityScore>> } => entry.productVisibility !== null);
  const latest = allRuns[allRuns.length - 1];
  const comp = topCompetitor(latest.competitor_scores);

  const series = history.map(({ run, productVisibility }) => ({
    label: new Date(run.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    value: productVisibility.mention_rate,
    querySetChanged: run.query_set_changed === true,
  }));

  const competitor = comp
    ? {
        name: comp.name.toUpperCase(),
        series: history.map(({ run }) => run.competitor_scores?.[comp.name]?.mention_rate ?? null),
      }
    : undefined;

  const siteUrl = (client as Pick<Client, "gsc_site_url"> | null)?.gsc_site_url;

  return (
    <div className="space-y-12">
      <div>
        <div className="font-mono text-[9px] tracking-[0.18em] uppercase mb-5" style={{ color: "var(--faint)" }}>
          PRODUCT VISIBILITY TIMELINE
        </div>
        <TimelineChart series={series} competitor={competitor} />
        {history.some(({ run }) => run.query_set_changed) && (
          <div className="font-mono text-[8px] tracking-[0.1em] mt-2" style={{ color: "#d4a017" }}>
            * QUERY SET CHANGED - TREND POINT IS NOT DIRECTLY COMPARABLE
          </div>
        )}
      </div>

      {latest.bucket_scores && Object.keys(latest.bucket_scores).length > 0 && (
        <div>
          <div className="font-mono text-[9px] tracking-[0.18em] uppercase mb-5" style={{ color: "var(--faint)" }}>
            VISIBILITY BY INTENT
          </div>
          <div className="grid grid-cols-2 gap-px" style={{ background: "var(--hair)", border: "1px solid var(--hair)" }}>
            {(["consideration", "awareness"] as const).map((b) => {
              const bs = b === "consideration" ? productVisibilityScore(latest) : contentAuthorityScore(latest);
              if (!bs || bs.intent_count === 0) return null;
              return (
                <div key={b} className="py-[14px] px-[18px]" style={{ background: "var(--ink)" }}>
                  <div className="font-mono text-[8px] tracking-[0.14em] uppercase mb-1" style={{ color: "var(--faint)" }}>
                    {BUCKET_LABELS[b]} · {bs.intent_count} INTENTS
                  </div>
                  <div className="font-display font-light text-[32px] leading-none" style={{ color: "var(--white)" }}>
                    {formatRate(bs.mention_rate)}
                  </div>
                  <div className="font-mono text-[9px] mt-1.5" style={{ color: "var(--mute)" }}>
                    cited {formatRate(bs.citation_rate)} · avg level {bs.avg_mention_level.toFixed(1)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {siteUrl && (
        <div>
          <div className="font-mono text-[9px] tracking-[0.18em] uppercase mb-5" style={{ color: "var(--faint)" }}>
            SEARCH CONSOLE
          </div>
          <div className="grid px-4 pb-3 border-b" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "16px", borderColor: "var(--hair)" }}>
            {["DATE", "CLICKS", "IMPRESSIONS", "CTR"].map((h) => (
              <div key={h} className="font-mono text-[8px] tracking-[0.18em]" style={{ color: "var(--faint)" }}>
                {h}
              </div>
            ))}
          </div>
          {allRuns.map((r) => (
            <div
              key={r.id}
              className="grid px-4 py-3 border-b font-mono text-[11px]"
              style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "16px", borderColor: "var(--hair)", color: "var(--white)" }}
            >
              <div>{new Date(r.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</div>
              <div>{(r.gsc_clicks ?? 0).toLocaleString()}</div>
              <div>{(r.gsc_impressions ?? 0).toLocaleString()}</div>
              <div>{formatRate(r.gsc_ctr ?? 0)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
