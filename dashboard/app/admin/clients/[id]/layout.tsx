import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";
import Link from "next/link";
import { SubTab } from "@/components/admin/SubTab";
import { TriggerRunButton } from "@/components/admin/TriggerRunButton";
import { rankAndGap, topCompetitor } from "@/lib/derive";
import { BUCKET_LABELS, contentAuthorityScore, productVisibilityScore } from "@/lib/intent-labels";
import { formatDelta, formatRate } from "@/lib/utils";
import { clientTabs } from "@/lib/client-tabs";
import type { Client, TrackerRun } from "@/lib/types";

export default async function ClientLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = createAdminClient();

  const { data: client, error: clientError } = await supabase
    .from("clients")
    .select("id, name, website_domain")
    .eq("id", id)
    .single();

  if (clientError) {
    if (clientError.code === "PGRST116") notFound();
    throw new Error(`Unable to load client ${id}: ${clientError.message}`);
  }
  if (!client) notFound();
  const c = client as Pick<Client, "id" | "name" | "website_domain">;

  const { data: runs } = await supabase
    .from("tracker_runs")
    .select("id, ran_at, aggregate_mention_rate, non_branded_mention_rate, bucket_scores, competitor_scores, query_set_changed")
    .eq("client_id", id)
    .order("ran_at", { ascending: false })
    .limit(2);

  const history = (runs as Pick<TrackerRun, "id" | "ran_at" | "aggregate_mention_rate" | "non_branded_mention_rate" | "bucket_scores" | "competitor_scores" | "query_set_changed">[]) || [];
  const latest = history[0] ?? null;
  const previous = history[1] ?? null;

  const rate = latest ? productVisibilityScore(latest)?.mention_rate ?? null : null;
  const contentCitationRate = latest ? contentAuthorityScore(latest)?.citation_rate ?? null : null;
  const previousRate = previous ? productVisibilityScore(previous)?.mention_rate ?? null : null;
  const comp = latest ? topCompetitor(latest.competitor_scores) : null;
  const rank = latest && rate != null ? rankAndGap(rate, latest.competitor_scores) : null;
  const delta =
    rate != null && previous
      ? formatDelta(rate, previousRate)
      : null;

  const tabs = clientTabs(id);

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2.5 mb-0 pb-3.5 border-b font-mono text-[9px] tracking-[0.14em]" style={{ borderColor: "var(--hair)" }}>
        <Link
          href="/admin/clients"
          className="uppercase transition-colors hover:text-[var(--white)]"
          style={{ color: "var(--faint)" }}
        >
          CLIENTS
        </Link>
        <span style={{ color: "var(--faint)", opacity: 0.4 }}>/</span>
        <span className="uppercase" style={{ color: "var(--mute)" }}>{c.name}</span>
      </div>

      {/* Client header */}
      <div className="pt-8 mb-0 flex items-start justify-between">
        <div>
          <h1
            className="font-display text-[48px] font-light leading-[0.95]"
            style={{ color: "var(--white)" }}
          >
            {c.name}
          </h1>
          <div
            className="font-mono text-[10px] tracking-[0.1em] mt-1.5"
            style={{ color: "var(--faint)" }}
          >
            {c.website_domain}
          </div>
          {/* Hero */}
          {!latest ? (
            <p className="font-serif italic text-base mt-4" style={{ color: "var(--mute)" }}>
              first run pending
            </p>
          ) : (
            <div className="mt-5">
              <div className="flex items-baseline gap-4 flex-wrap">
                <span
                  className="font-display text-[84px] font-light leading-none"
                  style={{ color: "var(--white)" }}
                >
                  {rate != null ? formatRate(rate) : "—"}
                </span>
                {delta && (
                  <span
                    className="font-mono text-lg"
                    style={{
                      color:
                        delta.direction === "up"
                          ? "var(--pos)"
                          : delta.direction === "down"
                            ? "var(--neg)"
                            : "var(--mute)",
                    }}
                  >
                    {delta.text}
                  </span>
                )}
                {comp && rank && (
                  <span className="font-mono text-[11px] leading-[1.6]" style={{ color: "var(--mute)" }}>
                    VS {comp.name.toUpperCase()} {formatRate(comp.rate)}
                    <br />#{rank.rank} OF {rank.total}
                  </span>
                )}
                {latest.query_set_changed && (
                  <span className="font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-1" style={{ color: "#d4a017", border: "1px solid #d4a017" }}>
                    query set changed
                  </span>
                )}
              </div>
              {latest.bucket_scores && (Object.keys(latest.bucket_scores).length > 0) && (
                <div className="flex gap-6 mt-3">
                  {(["consideration", "awareness"] as const).map((b) => {
                    const bs = b === "consideration" ? productVisibilityScore(latest) : contentAuthorityScore(latest);
                    if (!bs || bs.intent_count === 0) return null;
                    return (
                      <div key={b} className="font-mono text-[11px]" style={{ color: "var(--mute)" }}>
                        <span className="text-[8px] tracking-[0.14em] uppercase" style={{ color: "var(--faint)" }}>{BUCKET_LABELS[b]}</span>
                        <br />
                        <span style={{ color: "var(--white)" }}>{formatRate(bs.mention_rate)}</span>
                        <span className="text-[9px]" style={{ color: "var(--faint)" }}> · {bs.intent_count} intents</span>
                      </div>
                    );
                  })}
                </div>
              )}
              <div className="font-serif text-[13px] mt-2.5" style={{ color: "var(--mute)" }}>
                {contentCitationRate !== null ? (
                  <>Content Authority citation: {Math.round(contentCitationRate * 100)}%</>
                ) : (
                  "product visibility pending"
                )}
              </div>
            </div>
          )}
        </div>
        <TriggerRunButton clientId={id} />
      </div>

      {/* Sub-nav */}
      <div
        className="flex gap-0 mt-[22px] border-b mb-10"
        style={{ borderColor: "var(--hair)" }}
      >
        {tabs.map((tab) => (
          <SubTab key={tab.label} label={tab.label} href={tab.href} />
        ))}
      </div>

      {children}
    </div>
  );
}
