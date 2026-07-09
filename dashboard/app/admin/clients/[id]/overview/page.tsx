import { createAdminClient } from "@/lib/supabase/admin";
import { TimelineChart } from "@/components/charts/TimelineChart";
import { topCompetitor } from "@/lib/derive";
import { formatRate } from "@/lib/utils";
import type { Client, TrackerRun } from "@/lib/types";

type RunRow = Pick<
  TrackerRun,
  "id" | "ran_at" | "aggregate_mention_rate" | "non_branded_mention_rate" | "bucket_scores" | "competitor_scores" | "gsc_clicks" | "gsc_impressions" | "gsc_ctr"
>;

export default async function OverviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = createAdminClient();
  const [{ data: runs }, { data: client }] = await Promise.all([
    supabase
      .from("tracker_runs")
      .select("id, ran_at, aggregate_mention_rate, non_branded_mention_rate, bucket_scores, competitor_scores, gsc_clicks, gsc_impressions, gsc_ctr")
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

  const history = allRuns.filter((r) => (r.non_branded_mention_rate ?? r.aggregate_mention_rate) !== null);
  const latest = allRuns[allRuns.length - 1];
  const comp = topCompetitor(latest.competitor_scores);

  const series = history.map((r) => ({
    label: new Date(r.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    value: r.non_branded_mention_rate ?? r.aggregate_mention_rate,
  }));

  const competitor = comp
    ? {
        name: comp.name.toUpperCase(),
        series: history.map((r) => r.competitor_scores?.[comp.name]?.mention_rate ?? null),
      }
    : undefined;

  const siteUrl = (client as Pick<Client, "gsc_site_url"> | null)?.gsc_site_url;

  return (
    <div className="space-y-12">
      <div>
        <div className="font-mono text-[9px] tracking-[0.18em] uppercase mb-5" style={{ color: "var(--faint)" }}>
          VISIBILITY TIMELINE
        </div>
        <TimelineChart series={series} competitor={competitor} />
      </div>

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
