import type { ImprovementRun } from "@/lib/improvement-types";

export type RunPresentationMode = "technical_v1" | "legacy";

export type RunFunnelInput = {
  mode: RunPresentationMode;
  technicalStatus: string | null;
  technicalChecks: number;
  technicalFailures: number;
  technicalReviews: number;
  technicalUnknown: number;
  competitorLeads: number;
  matched: number;
  weak: number;
  contentGaps: number;
  scoredPages: number;
};

export type CrawlabilityBannerPresentation = {
  detailFallback: string;
  ctaLabel?: string;
  href?: string;
  guidance: string;
};

export function runPresentationMode(
  improvementRun: Pick<ImprovementRun, "run_mode"> | null,
): RunPresentationMode {
  return improvementRun?.run_mode === "technical_v1"
    ? "technical_v1"
    : "legacy";
}

export function formatCount(
  count: number,
  singular: string,
  plural = `${singular}s`,
): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

export function crawlabilityBannerPresentation(
  mode: RunPresentationMode,
  clientId: string,
): CrawlabilityBannerPresentation {
  if (mode === "technical_v1") {
    return {
      detailFallback: "review the latest run evidence for details",
      ctaLabel: "VIEW RUN EVIDENCE →",
      href: `/admin/clients/${clientId}/runs`,
      guidance:
        "REVIEW THE RUN EVIDENCE AND ACCESS GUIDANCE — VISIBILITY DATA REMAINS VALID",
    };
  }

  return {
    detailFallback: "see the priority-0 card for details",
    guidance:
      "DIAGNOSIS BELOW IS THE PRE-FIX BASELINE — VISIBILITY DATA REMAINS VALID",
  };
}

export function buildRunFunnel(input: RunFunnelInput): string {
  if (input.mode === "technical_v1") {
    const technicalAudit = input.technicalStatus === "completed"
      ? `${formatCount(input.technicalChecks, "technical check")} · ${formatCount(input.technicalFailures, "failure", "failures")} · ${formatCount(input.technicalReviews, "review")} · ${input.technicalUnknown} unknown`
      : input.technicalStatus
        ? `technical audit ${input.technicalStatus}`
        : "technical audit unavailable";

    return `AI visibility measured → ${technicalAudit} → ${formatCount(input.competitorLeads, "measured competitor lead")}`;
  }

  return `AI visibility measured → ${input.matched} matched · ${input.weak} weak · ${input.contentGaps} content gaps → ${input.scoredPages} pages scored → ${input.competitorLeads} competitive gaps`;
}
