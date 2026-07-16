export const dynamic = "force-dynamic";

import { createAdminClient } from "@/lib/supabase/admin";
import { fetchSchedules } from "@/lib/schedules";
import { biggestMovers, measuringCount, opsBadge, rankAndGap, topCompetitor } from "@/lib/derive";
import { BoardRow, type BoardRowData } from "@/components/board/BoardRow";
import { productVisibilityScore } from "@/lib/intent-labels";
import type { Client, TrackerRun, PromptScore } from "@/lib/types";

export default async function BoardPage() {
  const supabase = createAdminClient();
  const { data: clients } = await supabase
    .from("clients")
    .select("id, name, brand_name, created_at")
    .order("created_at", { ascending: true });
  const allClients = (clients as Pick<Client, "id" | "name" | "brand_name" | "created_at">[]) || [];

  const rows: BoardRowData[] = await Promise.all(
    allClients.map(async (client) => {
      const [{ data: runs }, { data: pipeline }, { data: pendingCards }, { data: verifiedCards }] =
        await Promise.all([
          supabase
            .from("tracker_runs")
            .select("id, ran_at, aggregate_mention_rate, non_branded_mention_rate, bucket_scores, competitor_scores")
            .eq("client_id", client.id)
            .order("ran_at", { ascending: false })
            .limit(6),
          supabase
            .from("pipeline_runs")
            .select("status, started_at")
            .eq("client_id", client.id)
            .order("started_at", { ascending: false })
            .limit(1),
          supabase
            .from("technical_audit_action_cards")
            .select("id, created_at")
            .eq("client_id", client.id)
            .not("status", "in", "(verified,rejected)"),
          supabase
            .from("technical_audit_action_cards")
            .select("status, created_at")
            .eq("client_id", client.id)
            .eq("status", "verified"),
        ]);

      const history = ((runs as Pick<TrackerRun, "id" | "ran_at" | "aggregate_mention_rate" | "non_branded_mention_rate" | "bucket_scores" | "competitor_scores">[]) || []);
      const latest = history[0] ?? null;
      const previous = history[1] ?? null;

      let movers: ReturnType<typeof biggestMovers> = [];
      if (latest && previous) {
        const { data: scores } = await supabase
          .from("prompt_scores")
            .select("run_id, query_id, query, bucket, llm, mention_rate, citation_rate")
            .in("run_id", [latest.id, previous.id]);
        const all = ((scores as (Pick<PromptScore, "run_id" | "query_id" | "query" | "bucket" | "llm" | "mention_rate" | "citation_rate">)[]) || []).filter((s) => s.bucket !== "branded");
        movers = biggestMovers(
          all.filter((s) => s.run_id === latest.id),
          all.filter((s) => s.run_id === previous.id)
        );
      }

      const pending = pendingCards || [];
      // Server component rendered per-request (force-dynamic); reading the clock
      // to compute card age is intentional.
      const oldestPendingDays = pending.length
        ? // eslint-disable-next-line react-hooks/purity
          Math.floor((Date.now() - Math.min(...pending.map((c) => new Date(c.created_at).getTime()))) / 86400000)
        : null;

      const badge = opsBadge({
        latestPipelineStatus: pipeline?.[0]?.status ?? null,
        pendingCount: pending.length,
        oldestPendingDays,
        measuring: measuringCount(
          (verifiedCards || []).map((card) => ({ ...card, status: "implemented" })),
          latest?.ran_at ?? null
        ),
        hasRun: !!latest,
      });

      const rate = latest ? productVisibilityScore(latest)?.mention_rate ?? null : null;
      const previousRate = previous ? productVisibilityScore(previous)?.mention_rate ?? null : null;
      const comp = latest ? topCompetitor(latest.competitor_scores) : null;
      const rank = latest && rate != null ? rankAndGap(rate, latest.competitor_scores) : null;

      return {
        clientId: client.id,
        name: client.brand_name || client.name,
        rate,
        delta:
          rate != null && previousRate != null
            ? rate - previousRate
            : null,
        competitor: comp,
        rank,
        movers,
        sparkline: [...history].reverse().map((r) => productVisibilityScore(r)?.mention_rate ?? null),
        badge,
        pendingCount: pending.length,
        firstRunPending: !latest,
      };
    })
  );

  rows.sort((a, b) => (a.delta ?? 0) - (b.delta ?? 0));

  const improving = rows.filter((r) => (r.delta ?? 0) > 0.005).length;
  const declining = rows.filter((r) => (r.delta ?? 0) < -0.005).length;
  const flat = rows.length - improving - declining;
  const totalCards = rows.reduce((s, r) => s + r.pendingCount, 0);
  const errors = rows.filter((r) => r.badge.kind === "error").length;

  const schedules = await fetchSchedules();
  const upcoming = schedules
    .filter((s) => s.next_run)
    .sort((a, b) => (a.next_run! < b.next_run! ? -1 : 1))
    .slice(0, 3);

  const nextRunByClient = new Map(
    schedules.filter((s) => s.next_run).map((s) => [s.client_id, s.next_run as string])
  );

  const formatNextRun = (iso: string) => {
    const d = new Date(iso);
    const weekday = d.toLocaleDateString("en-US", { weekday: "short", timeZone: "UTC" });
    const time = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "UTC" });
    return `${weekday} ${time}`;
  };

  return (
    <>
      <div className="mb-10">
        <h1 className="font-display text-[52px] font-light leading-[0.96]" style={{ color: "var(--white)" }}>
          Board
        </h1>
        <p className="font-serif italic text-base mt-2" style={{ color: "var(--mute)" }}>
          Product Visibility across the portfolio
        </p>
      </div>

      {rows.length > 0 && (
        <div className="mb-8 font-mono text-[9px] tracking-[0.14em] uppercase" style={{ color: "var(--faint)" }}>
          <span style={{ color: "var(--pos)" }}>{improving} IMPROVING</span>
          {" · "}
          <span style={{ color: "var(--neg)" }}>{declining} DECLINING</span>
          {" · "}
          <span>{flat} FLAT</span>
          {" — "}
          <span style={{ color: totalCards > 0 ? "#d4a017" : "var(--faint)" }}>{totalCards} CARDS TO REVIEW</span>
          {" — "}
          <span style={{ color: errors > 0 ? "var(--neg)" : "var(--faint)" }}>{errors} ERRORS</span>
        </div>
      )}

      {allClients.length === 0 ? (
        <p className="font-serif italic text-base py-10" style={{ color: "var(--mute)" }}>
          No clients yet.
        </p>
      ) : (
        <div style={{ borderTop: "1px solid var(--hair)" }}>
          {rows.map((row) => (
            <BoardRow key={row.clientId} row={row} nextRunLabel={nextRunByClient.get(row.clientId) ? formatNextRun(nextRunByClient.get(row.clientId)!) : undefined} />
          ))}
        </div>
      )}

      {upcoming.length > 0 && (
        <div className="mt-10 pt-6 flex items-baseline gap-6" style={{ borderTop: "1px solid var(--hair)" }}>
          <span className="font-mono text-[8px] tracking-[0.14em] uppercase" style={{ color: "var(--faint)" }}>
            NEXT RUNS
          </span>
          {upcoming.map((s) => (
            <span key={s.client_id} className="font-mono text-[9px]" style={{ color: "var(--faint)" }}>
              {s.client_name} {formatNextRun(s.next_run as string)}
            </span>
          ))}
        </div>
      )}
    </>
  );
}
