export type RunPresentationMode = "technical_v1" | "legacy";

export type RunFunnelInput = {
  mode: RunPresentationMode;
  technicalStatus: string | null;
  technicalChecks: number;
  technicalFailures: number;
  technicalReviews: number;
  technicalUnknown: number;
  competitorLeads: number;
  cards: number;
  matched: number;
  weak: number;
  contentGaps: number;
  scoredPages: number;
};

export function runPresentationMode(
  technicalAuditRun: { id: string } | null,
): RunPresentationMode {
  return technicalAuditRun ? "technical_v1" : "legacy";
}

export function buildRunFunnel(input: RunFunnelInput): string {
  if (input.mode === "technical_v1") {
    const technicalAudit = input.technicalStatus === "completed"
      ? `${input.technicalChecks} technical checks · ${input.technicalFailures} failures · ${input.technicalReviews} reviews · ${input.technicalUnknown} unknown`
      : `technical audit ${input.technicalStatus}`;

    return `AI visibility measured → ${technicalAudit} → ${input.competitorLeads} measured competitor leads → ${input.cards} manual cards`;
  }

  return `AI visibility measured → ${input.matched} matched · ${input.weak} weak · ${input.contentGaps} content gaps → ${input.scoredPages} pages scored → ${input.competitorLeads} competitive gaps → ${input.cards} cards`;
}
