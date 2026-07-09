import { createAdminClient } from "@/lib/supabase/admin";
import { notFound } from "next/navigation";
import Link from "next/link";
import { SubTab } from "@/components/admin/SubTab";
import { TriggerRunButton } from "@/components/admin/TriggerRunButton";
import { fetchSchedules } from "@/lib/schedules";
import { aggregateCitationRate, rankAndGap, topCompetitor } from "@/lib/derive";
import { formatDelta, formatRate } from "@/lib/utils";
import type { Client, PromptScore, TrackerRun } from "@/lib/types";
import type { CrawlabilityReport, ImprovementRun } from "@/lib/improvement-types";

const CRAWL_CHECK_KEYS = ["robots_txt", "cdn_blocks", "js_rendering"] as const;

function formatNextRun(iso: string): string {
  const d = new Date(iso);
  const weekday = d.toLocaleDateString("en-US", { weekday: "short", timeZone: "UTC" });
  const time = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "UTC" });
  return `${weekday} ${time}`;
}

export default async function ClientLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = createAdminClient();

  const { data: client } = await supabase
    .from("clients")
    .select("id, name, website_domain, cycle_frequency, cycle_day")
    .eq("id", id)
    .single();

  if (!client) notFound();
  const c = client as Pick<Client, "id" | "name" | "website_domain" | "cycle_frequency" | "cycle_day">;

  const [{ data: runs }, { data: improvementRuns }] = await Promise.all([
    supabase
      .from("tracker_runs")
      .select("id, ran_at, aggregate_mention_rate, non_branded_mention_rate, bucket_scores, competitor_scores, query_set_changed")
      .eq("client_id", id)
      .order("ran_at", { ascending: false })
      .limit(2),
    supabase
      .from("improvement_runs")
      .select("id, ran_at, crawlability_report")
      .eq("client_id", id)
      .order("ran_at", { ascending: false })
      .limit(1),
  ]);

  const history = (runs as Pick<TrackerRun, "id" | "ran_at" | "aggregate_mention_rate" | "non_branded_mention_rate" | "bucket_scores" | "competitor_scores" | "query_set_changed">[]) || [];
  const latest = history[0] ?? null;
  const previous = history[1] ?? null;

  let citationRate: number | null = null;
  if (latest) {
    const { data: scores } = await supabase
      .from("prompt_scores")
      .select("query, bucket, llm, mention_rate, citation_rate")
      .eq("run_id", latest.id);
    citationRate = aggregateCitationRate(
      ((scores as Pick<PromptScore, "query" | "bucket" | "llm" | "mention_rate" | "citation_rate">[]) || []).filter((s) => s.bucket !== "branded")
    );
  }

  const rate = latest?.non_branded_mention_rate ?? latest?.aggregate_mention_rate ?? null;
  const comp = latest ? topCompetitor(latest.competitor_scores) : null;
  const rank = latest && rate != null ? rankAndGap(rate, latest.competitor_scores) : null;
  const delta =
    rate != null && previous
      ? formatDelta(rate, previous.non_branded_mention_rate ?? previous.aggregate_mention_rate)
      : null;

  const schedules = await fetchSchedules();
  const schedule = schedules.find((s) => s.client_id === id);
  const nextRunLabel = schedule?.next_run ? formatNextRun(schedule.next_run) : null;

  const improvementRun = (improvementRuns as Pick<ImprovementRun, "id" | "ran_at" | "crawlability_report">[])?.[0];
  const report = improvementRun?.crawlability_report as CrawlabilityReport | undefined;
  const blocker = report?.has_critical_blocker === true;
  const failing = blocker
    ? CRAWL_CHECK_KEYS.filter((k) => report?.[k]?.status === "fail").map((k) => ({
        name: k,
        detail: report?.[k]?.detail ?? k,
      }))
    : [];

  const tabs = [
    { label: "OVERVIEW", href: `/admin/clients/${id}/overview` },
    { label: "QUERIES", href: `/admin/clients/${id}/queries` },
    { label: "PAGES", href: `/admin/clients/${id}/pages` },
    { label: "RUNS", href: `/admin/clients/${id}/runs` },
    { label: "CARDS", href: `/admin/clients/${id}/cards` },
    { label: "CONFIG", href: `/admin/clients/${id}/config` },
    { label: "REPORTS", href: `/admin/clients/${id}/reports` },
  ];

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
          <div
            className="font-mono text-[8px] tracking-[0.06em] mt-1"
            style={{ color: "var(--faint)", opacity: 0.7 }}
          >
            {c.cycle_frequency === "monthly" ? "Monthly" : c.cycle_frequency === "biweekly" ? "Bi-weekly" : "Weekly"} · {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][c.cycle_day ?? 1]} 2:00 AM UTC
            {nextRunLabel ? ` · NEXT RUN ${nextRunLabel}` : ""}
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
              <div className="font-serif text-[13px] mt-2.5" style={{ color: "var(--mute)" }}>
                {citationRate !== null ? (
                  <>
                    cited as source: {Math.round(citationRate * 100)}% of non-branded mentions{" "}
                    <span style={{ color: "var(--faint)" }}> · branded deferred</span>
                  </>
                ) : (
                  "no mentions yet this cycle"
                )}
              </div>
            </div>
          )}
        </div>
        <TriggerRunButton clientId={id} />
      </div>

      {/* Crawlability blocker banner */}
      {blocker && (
        <div className="mt-4 px-5 py-3.5" style={{ background: "rgba(232,154,160,0.08)", border: "1px solid var(--neg)" }}>
          <div className="font-mono text-[9px] tracking-[0.14em] uppercase mb-1" style={{ color: "var(--neg)" }}>
            CRAWLABILITY BLOCKER — AI CRAWLERS CANNOT ACCESS THE SITE
          </div>
          <div className="font-serif text-[13px]" style={{ color: "var(--white)" }}>
            {failing.length > 0
              ? failing.map((f) => `${f.name}: ${f.detail}`).join(" · ")
              : "see the priority-0 card for details"}
          </div>
          <Link href="/admin/approvals" className="font-mono text-[9px] tracking-[0.1em] uppercase underline" style={{ color: "var(--neg)" }}>
            VIEW FIX-CRAWLABILITY CARD →
          </Link>
          <div className="font-mono text-[8px] mt-1" style={{ color: "var(--faint)" }}>
            DIAGNOSIS BELOW IS THE PRE-FIX BASELINE — VISIBILITY DATA REMAINS VALID
          </div>
        </div>
      )}

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
