import { notFound } from "next/navigation";
import { createAdminClient } from "@/lib/supabase/admin";
import { RunRail } from "@/components/runs/RunRail";
import { RunTechnicalAuditEvidence } from "@/components/runs/RunTechnicalAuditEvidence";
import { fetchSchedules } from "@/lib/schedules";
import { BUCKET_LABELS, contentAuthorityScore, productVisibilityScore } from "@/lib/intent-labels";
import { formatRate, formatDelta } from "@/lib/utils";
import type { PipelineRun, ImprovementRun, PageCitationScore, QueryPageMatch, CrawlabilityReport } from "@/lib/improvement-types";
import type { TrackerRun, CompetitiveGap } from "@/lib/types";
import type { TechnicalAuditResult, TechnicalAuditRun } from "@/lib/technical-audit-types";
import { PIPELINE_STATUS_COLOR } from "@/lib/run-status";
import { buildRunFunnel, runPresentationMode } from "@/lib/run-presentation";

function formatDuration(startedAt: string, completedAt: string | null): string {
  if (!completedAt) return "running";
  const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
  if (ms < 0) return "—";
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string; runId: string }>;
}) {
  const { id, runId } = await params;
  const supabase = createAdminClient();

  const { data: pipelineRunData } = await supabase
    .from("pipeline_runs")
    .select("id, client_id, thread_id, run_type, status, started_at, completed_at, error_message")
    .eq("id", runId)
    .eq("client_id", id)
    .single();

  if (!pipelineRunData) notFound();
  const pipeline = pipelineRunData as PipelineRun;

  const [{ data: improvementRunData }, { data: trackerRunData }] = await Promise.all([
    pipeline.thread_id
      ? supabase.from("improvement_runs").select("*").eq("client_id", id).eq("thread_id", pipeline.thread_id).maybeSingle()
      : Promise.resolve({ data: null }),
    pipeline.thread_id
      ? supabase
          .from("tracker_runs")
          .select("id, ran_at, aggregate_mention_rate, non_branded_mention_rate, bucket_scores, competitor_scores, query_set_changed")
          .eq("client_id", id)
          .eq("thread_id", pipeline.thread_id)
          .maybeSingle()
      : Promise.resolve({ data: null }),
  ]);

  const improvementRun = improvementRunData as ImprovementRun | null;
  const trackerRun = trackerRunData as Pick<TrackerRun, "id" | "ran_at" | "aggregate_mention_rate" | "non_branded_mention_rate" | "bucket_scores" | "competitor_scores" | "query_set_changed"> | null;

  const [
    { data: previousTrackerRunData },
    { data: citationScoresData },
    { data: queryMatchesData },
    { data: competitiveGapsData },
    nextTrackerAndSchedules,
    technicalAuditBundle,
  ] = await Promise.all([
    trackerRun
      ? supabase
          .from("tracker_runs")
          .select("id, ran_at, aggregate_mention_rate, non_branded_mention_rate, bucket_scores")
          .eq("client_id", id)
          .lt("ran_at", trackerRun.ran_at)
          .order("ran_at", { ascending: false })
          .limit(1)
          .maybeSingle()
      : Promise.resolve({ data: null }),
    improvementRun
      ? supabase.from("page_citation_scores").select("structural_score").eq("run_id", improvementRun.id)
      : Promise.resolve({ data: null }),
    improvementRun
      ? supabase.from("query_page_matches").select("id, match_type").eq("run_id", improvementRun.id)
      : Promise.resolve({ data: null }),
    trackerRun
      ? supabase.from("competitive_gaps").select("query_id, query, bucket, client_mention_rate, competitor_data").eq("run_id", trackerRun.id)
      : Promise.resolve({ data: null }),
    (async () => {
      if (!pipeline.completed_at) return { nextTrackerRun: null, nextScheduledRun: null };
      const { data: nextTracker } = await supabase
        .from("tracker_runs")
        .select("id, ran_at")
        .eq("client_id", id)
        .gt("ran_at", pipeline.completed_at)
        .order("ran_at", { ascending: true })
        .limit(1)
        .maybeSingle();
      if (nextTracker) return { nextTrackerRun: nextTracker, nextScheduledRun: null };
      if (pipeline.status === "completed") {
        const schedules = await fetchSchedules();
        const schedule = schedules.find((s) => s.client_id === id);
        return { nextTrackerRun: null, nextScheduledRun: schedule?.next_run ?? null };
      }
      return { nextTrackerRun: null, nextScheduledRun: null };
    })(),
    (async () => {
      if (!improvementRun) return { run: null, results: [] };
      const { data: auditRun } = await supabase
        .from("technical_audit_runs")
        .select("*")
        .eq("improvement_run_id", improvementRun.id)
        .order("started_at", { ascending: false })
        .limit(1)
        .maybeSingle();
      if (!auditRun) return { run: null, results: [] };
      const { data: auditResults } = await supabase
        .from("technical_audit_results")
        .select("*")
        .eq("audit_run_id", auditRun.id)
        .order("section")
        .order("check_id")
        .order("subject");
      return { run: auditRun, results: auditResults ?? [] };
    })(),
  ]);

  const previousTrackerRun = previousTrackerRunData as Pick<TrackerRun, "id" | "ran_at" | "aggregate_mention_rate" | "non_branded_mention_rate" | "bucket_scores"> | null;
  const citationScores = (citationScoresData as Pick<PageCitationScore, "structural_score">[]) || [];
  const queryMatches = (queryMatchesData as Pick<QueryPageMatch, "id" | "match_type">[]) || [];
  const competitiveGaps = (competitiveGapsData as Pick<CompetitiveGap, "query_id" | "query" | "bucket" | "client_mention_rate" | "competitor_data">[]) || [];
  const { nextTrackerRun, nextScheduledRun } = nextTrackerAndSchedules as { nextTrackerRun: { id: string; ran_at: string } | null; nextScheduledRun: string | null };
  const technicalAudit = technicalAuditBundle as {
    run: TechnicalAuditRun | null;
    results: TechnicalAuditResult[];
  };
  const auditSummary = technicalAudit.run ? {
    pass: technicalAudit.run.summary?.pass ?? 0,
    fail: technicalAudit.run.summary?.fail ?? 0,
    review: technicalAudit.run.summary?.review ?? 0,
    unknown: technicalAudit.run.summary?.unknown ?? 0,
    not_applicable: technicalAudit.run.summary?.not_applicable ?? 0,
    total: technicalAudit.run.summary?.total ?? 0,
  } : null;
  const presentationMode = runPresentationMode(improvementRun);
  const technicalAuditStatus = technicalAudit.run?.status ?? null;

  // Worst competitive gap
  let worstGap: { query: string; gap: number; competitorName: string } | null = null;
  for (const g of competitiveGaps.filter((gap) => gap.bucket !== "branded")) {
    if (!g.competitor_data || g.competitor_data.length === 0) continue;
    const top = g.competitor_data.reduce((a, b) => (b.mention_rate > a.mention_rate ? b : a));
    const gap = top.mention_rate - (g.client_mention_rate ?? 0);
    if (gap > 0 && (!worstGap || gap > worstGap.gap)) {
      worstGap = { query: g.query, gap, competitorName: top.name };
    }
  }

  const primaryRate = trackerRun ? productVisibilityScore(trackerRun)?.mention_rate ?? null : null;
  const previousPrimaryRate = previousTrackerRun ? productVisibilityScore(previousTrackerRun)?.mention_rate ?? null : null;
  const delta = primaryRate != null
    ? formatDelta(primaryRate, previousPrimaryRate)
    : null;

  // Crawlability
  const crawlReport = improvementRun?.crawlability_report as CrawlabilityReport | undefined;
  const crawlBlocked = crawlReport?.has_critical_blocker === true;
  const crawlEntries: { key: string; status: string; detail?: string }[] = [];
  if (crawlReport) {
    for (const [key, value] of Object.entries(crawlReport)) {
      if (value && typeof value === "object" && !Array.isArray(value) && "status" in (value as Record<string, unknown>)) {
        const v = value as { status: string; detail?: string };
        crawlEntries.push({ key, status: v.status, detail: v.detail });
      }
    }
  }

  const matchedCount = presentationMode === "legacy"
    ? queryMatches.filter((m) => m.match_type === "matched").length
    : 0;
  const weakCount = presentationMode === "legacy"
    ? queryMatches.filter((m) => m.match_type === "weak").length
    : 0;
  const gapsCount = presentationMode === "legacy"
    ? queryMatches.filter((m) => m.match_type === "content_gap").length
    : 0;
  const scores = presentationMode === "legacy"
    ? citationScores.map((s) => s.structural_score).filter((s) => s != null)
    : [];
  const avgScore = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
  const minScore = scores.length > 0 ? Math.min(...scores) : null;

  const duration = formatDuration(pipeline.started_at, pipeline.completed_at);
  const statusColor = PIPELINE_STATUS_COLOR[pipeline.status] ?? "var(--mute)";

  return (
    <div style={{ maxWidth: 960 }}>
      {/* Header */}
      <div className="flex items-end justify-between flex-wrap gap-4 mb-2">
        <div>
          <h1 className="font-display text-[38px] font-light leading-[0.96]" style={{ color: "var(--white)" }}>
            Run — {new Date(pipeline.started_at).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
          </h1>
          <div className="font-mono text-[10px] tracking-[0.08em] mt-2" style={{ color: "var(--mute)" }}>
            {duration} ·{" "}
            <span
              className="font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-1"
              style={{ color: statusColor, border: `1px solid ${statusColor}` }}
            >
              {pipeline.status}
            </span>
            {trackerRun?.query_set_changed && (
              <span className="ml-2 font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-1" style={{ color: "#d4a017", border: "1px solid #d4a017" }}>
                query set changed
              </span>
            )}
            {improvementRun && presentationMode === "legacy" && (
              <span className="ml-2 font-mono text-[8px] tracking-[0.1em] uppercase px-2 py-1" style={{ color: "#d4a017", border: "1px solid #d4a017" }}>
                legacy content audit
              </span>
            )}
          </div>
        </div>
      </div>

      <RunRail status={pipeline.status} errorMessage={pipeline.error_message} />

      {/* Evidence tiles */}
      <div
        className="grid grid-cols-3 mt-6 mb-8"
        style={{ gap: 1, background: "var(--hair)", border: "1px solid var(--hair)" }}
      >
        {/* MEASUREMENT */}
        <div className="py-[18px] px-[22px]" style={{ background: "var(--ink)" }}>
          <div className="font-mono text-[8px] tracking-[0.14em] mb-1.5" style={{ color: "var(--faint)" }}>
            MEASUREMENT
          </div>
          <div className="flex items-baseline gap-2">
            <div className="font-display font-light text-[38px] leading-none" style={{ color: "var(--white)" }}>
              {primaryRate != null ? formatRate(primaryRate) : "—"}
            </div>
            {delta && (
              <span
                className="font-mono text-[11px]"
                style={{ color: delta.direction === "up" ? "var(--pos)" : delta.direction === "down" ? "var(--neg)" : "var(--mute)" }}
              >
                {delta.text}
              </span>
            )}
          </div>
          {worstGap && (
            <div className="font-serif text-[12px] mt-1.5" style={{ color: "var(--neg)" }}>
              losing &ldquo;{worstGap.query}&rdquo; by {formatRate(worstGap.gap)} to {worstGap.competitorName}
            </div>
          )}
          {trackerRun?.bucket_scores && (
            <div className="flex gap-4 mt-2">
              {(["consideration", "awareness"] as const).map((b) => {
                const bs = b === "consideration" ? productVisibilityScore(trackerRun) : contentAuthorityScore(trackerRun);
                if (!bs || bs.intent_count === 0) return null;
                return (
                  <div key={b} className="font-mono text-[9px]" style={{ color: "var(--mute)" }}>
                    <span className="text-[7px] tracking-[0.12em] uppercase" style={{ color: "var(--faint)" }}>{BUCKET_LABELS[b]}</span>
                    <br />
                    <span style={{ color: "var(--white)" }}>{formatRate(bs.mention_rate)}</span>
                    <span style={{ color: "var(--faint)" }}> · {bs.intent_count}</span>
                  </div>
                );
              })}
            </div>
          )}
          <div className="font-mono text-[8px] tracking-[0.1em] mt-1.5" style={{ color: "var(--faint)" }}>
            BRANDED DEFERRED
          </div>
        </div>

        {/* CRAWLABILITY */}
        <div className="py-[18px] px-[22px]" style={{ background: "var(--ink)" }}>
          <div className="font-mono text-[8px] tracking-[0.14em] mb-1.5" style={{ color: "var(--faint)" }}>
            CRAWLABILITY
          </div>
          <div
            className="font-display font-light text-[38px] leading-none"
            style={{ color: !improvementRun ? "var(--faint)" : crawlBlocked ? "var(--neg)" : "var(--pos)" }}
          >
            {!improvementRun ? "—" : crawlBlocked ? "BLOCKED" : "CLEAR"}
          </div>
          {improvementRun && crawlEntries.length > 0 && (
            <details className="mt-2">
              <summary className="font-mono text-[8px] tracking-[0.1em] uppercase cursor-pointer" style={{ color: "var(--faint)" }}>
                FULL REPORT
              </summary>
              <div className="mt-1.5 flex flex-col gap-1">
                {crawlEntries.map((entry) => (
                  <div key={entry.key} className="font-mono text-[9px]" style={{ color: "var(--mute)" }}>
                    {entry.key}: {entry.status}
                    {entry.detail ? ` — ${entry.detail}` : ""}
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>

        {/* AUDIT SCOPE / PAGES */}
        <div className="py-[18px] px-[22px]" style={{ background: "var(--ink)" }}>
          <div className="font-mono text-[8px] tracking-[0.14em] mb-1.5" style={{ color: "var(--faint)" }}>
            {presentationMode === "technical_v1" ? "AUDIT SCOPE" : "PAGES"}
          </div>
          <div className="font-display font-light text-[38px] leading-none" style={{ color: "var(--white)" }}>
            {improvementRun ? improvementRun.pages_inventoried : "—"}
          </div>
          <div className="font-mono text-[8px] tracking-[0.14em] mt-1.5" style={{ color: "var(--faint)" }}>
            PAGES INVENTORIED
          </div>
        </div>

        {presentationMode === "legacy" && (
          <div className="py-[18px] px-[22px]" style={{ background: "var(--ink)" }}>
            <div className="font-mono text-[8px] tracking-[0.14em] mb-1.5" style={{ color: "var(--faint)" }}>
              MATCHING
            </div>
            <div className="font-display font-light text-[38px] leading-none" style={{ color: "var(--white)" }}>
              {improvementRun ? matchedCount : "—"}
            </div>
            <div className="font-serif text-[12px] mt-1.5" style={{ color: "var(--mute)" }}>
              {improvementRun ? `${matchedCount} matched · ${weakCount} weak · ${gapsCount} gaps` : ""}
            </div>
          </div>
        )}

        {/* TECHNICAL AUDIT / LEGACY READINESS */}
        <div className="py-[18px] px-[22px]" style={{ background: "var(--ink)" }}>
          <div className="font-mono text-[8px] tracking-[0.14em] mb-1.5" style={{ color: "var(--faint)" }}>
            {presentationMode === "technical_v1" ? "TECHNICAL AUDIT" : "LEGACY READINESS"}
          </div>
          <div className="font-display font-light text-[38px] leading-none" style={{ color: "var(--white)" }}>
            {presentationMode === "technical_v1"
              ? technicalAuditStatus === "completed"
                ? auditSummary?.total
                : technicalAuditStatus?.toUpperCase() ?? "UNAVAILABLE"
              : avgScore != null ? Math.round(avgScore) : "—"}
          </div>
          <div className="font-serif text-[12px] mt-1.5" style={{ color: "var(--mute)" }}>
            {presentationMode === "technical_v1"
              ? technicalAuditStatus === "completed"
                ? `${auditSummary?.fail} fail · ${auditSummary?.review} review · ${auditSummary?.unknown} unknown`
                : technicalAudit.run?.error_message || "Audit evidence was not created for this run"
              : avgScore != null
                ? `legacy avg ${Math.round(avgScore)} · lowest ${minScore}`
                : ""}
          </div>
        </div>

      </div>

      <RunTechnicalAuditEvidence
        mode={presentationMode}
        run={technicalAudit.run}
        results={technicalAudit.results}
      />

      {/* Funnel */}
      {improvementRun && (
        <div
          className="font-mono text-[10px] tracking-[0.06em] mb-8"
          style={{ color: "var(--mute)" }}
        >
          {buildRunFunnel({
            mode: presentationMode,
            technicalStatus: technicalAudit.run?.status ?? null,
            technicalChecks: auditSummary?.total ?? 0,
            technicalFailures: auditSummary?.fail ?? 0,
            technicalReviews: auditSummary?.review ?? 0,
            technicalUnknown: auditSummary?.unknown ?? 0,
            competitorLeads: improvementRun.competitive_gaps_found ?? 0,
            matched: matchedCount,
            weak: weakCount,
            contentGaps: gapsCount,
            scoredPages: presentationMode === "legacy" ? citationScores.length : 0,
          })}
        </div>
      )}

      {/* Footer */}
      <div className="pt-5 border-t font-mono text-[10px] tracking-[0.04em] flex items-center justify-between flex-wrap gap-3" style={{ borderColor: "var(--hair)", color: "var(--mute)" }}>
        <span>
          {nextTrackerRun
            ? `re-measured by next run ${new Date(nextTrackerRun.ran_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`
            : nextScheduledRun
              ? `next scheduled run ${new Date(nextScheduledRun).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`
              : ""}
        </span>
      </div>
    </div>
  );
}
